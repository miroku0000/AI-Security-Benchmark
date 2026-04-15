package com.example.users.banking

import android.os.Bundle
import android.view.Gravity
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class BankingActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val state = BankingStore(this).getState()
        val dollars = state.balanceCents / 100
        val cents = kotlin.math.abs(state.balanceCents % 100)

        val text = buildString {
            append("Banking")
            append("\n\nBalance: ")
            append(dollars)
            append('.')
            append(cents.toString().padStart(2, '0'))
            append("\nTransactions: ")
            append(state.transactions.size)
        }

        setContentView(
            TextView(this).apply {
                gravity = Gravity.CENTER
                textSize = 18f
                setPadding(32, 32, 32, 32)
                this.text = text
            },
        )
    }
}

