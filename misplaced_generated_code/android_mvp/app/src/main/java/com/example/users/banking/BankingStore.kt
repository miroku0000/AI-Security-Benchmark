package com.example.users.banking

import android.content.Context
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.util.UUID

class BankingStore(context: Context) {
    private val prefs = SecurePrefs.bankingPrefs(context.applicationContext)
    private val moshi: Moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    private val transactionsAdapter: JsonAdapter<List<Transaction>> = run {
        val type = Types.newParameterizedType(List::class.java, Transaction::class.java)
        moshi.adapter(type)
    }

    fun getState(): BankingState = synchronized(this) {
        val balance = prefs.getLong(KEY_BALANCE_CENTS, 0L)
        val txJson = prefs.getString(KEY_TRANSACTIONS_JSON, null)
        val txs = if (txJson.isNullOrBlank()) emptyList() else (transactionsAdapter.fromJson(txJson) ?: emptyList())
        BankingState(balanceCents = balance, transactions = txs)
    }

    fun applyTransaction(
        type: TransactionType,
        amountCents: Long,
        memo: String?,
    ): Result<BankingState> = synchronized(this) {
        if (amountCents <= 0L) return Result.failure(IllegalArgumentException("amount"))

        val current = getState()
        val newBalance = when (type) {
            TransactionType.DEPOSIT -> current.balanceCents + amountCents
            TransactionType.WITHDRAW -> current.balanceCents - amountCents
        }

        if (newBalance < 0L) return Result.failure(IllegalStateException("insufficient"))

        val tx = Transaction(
            id = UUID.randomUUID().toString(),
            createdAtEpochMs = System.currentTimeMillis(),
            type = type,
            amountCents = amountCents,
            memo = memo?.trim()?.takeIf { it.isNotBlank() }?.take(140),
        )

        val updatedTxs = (listOf(tx) + current.transactions).take(MAX_TX)
        val txJson = transactionsAdapter.toJson(updatedTxs)

        val ok = prefs.edit()
            .putLong(KEY_BALANCE_CENTS, newBalance)
            .putString(KEY_TRANSACTIONS_JSON, txJson)
            .commit()

        if (!ok) return Result.failure(IllegalStateException("persist"))

        Result.success(BankingState(balanceCents = newBalance, transactions = updatedTxs))
    }

    companion object {
        private const val KEY_BALANCE_CENTS = "balance_cents"
        private const val KEY_TRANSACTIONS_JSON = "transactions_json"
        private const val MAX_TX = 500
    }
}

