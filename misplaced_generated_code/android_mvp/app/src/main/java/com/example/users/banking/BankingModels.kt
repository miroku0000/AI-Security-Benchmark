package com.example.users.banking

enum class TransactionType {
    DEPOSIT,
    WITHDRAW,
}

data class Transaction(
    val id: String,
    val createdAtEpochMs: Long,
    val type: TransactionType,
    val amountCents: Long,
    val memo: String?,
)

data class BankingState(
    val balanceCents: Long,
    val transactions: List<Transaction>,
)

