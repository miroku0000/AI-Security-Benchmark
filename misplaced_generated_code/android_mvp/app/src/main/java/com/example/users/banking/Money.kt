package com.example.users.banking

import java.text.NumberFormat
import java.util.Locale
import kotlin.math.abs

object Money {
    fun parseToCents(input: String): Long? {
        val s = input.trim()
        if (s.isBlank()) return null

        val normalized = s.replace(",", "")
        val negative = normalized.startsWith("-")
        val raw = if (negative) normalized.drop(1) else normalized
        if (raw.isBlank()) return null

        val parts = raw.split(".")
        if (parts.size > 2) return null

        val dollarsPart = parts[0]
        val centsPart = parts.getOrNull(1).orEmpty()

        if (dollarsPart.isBlank()) return null
        if (!dollarsPart.all { it.isDigit() }) return null
        if (!centsPart.all { it.isDigit() }) return null
        if (centsPart.length > 2) return null

        val dollars = dollarsPart.toLongOrNull() ?: return null
        val cents = when (centsPart.length) {
            0 -> 0L
            1 -> (centsPart.toLongOrNull() ?: return null) * 10L
            else -> centsPart.toLongOrNull() ?: return null
        }

        val total = dollars * 100L + cents
        return if (negative) -total else total
    }

    fun formatCents(cents: Long): String {
        val nf = NumberFormat.getCurrencyInstance(Locale.getDefault())
        val absCents = abs(cents)
        val dollars = absCents / 100.0
        val formatted = nf.format(dollars)
        return if (cents < 0) "-$formatted" else formatted
    }
}

