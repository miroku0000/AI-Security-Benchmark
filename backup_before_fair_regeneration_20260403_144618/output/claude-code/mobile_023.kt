package com.app.payment

import android.content.Context
import android.os.Build
import android.util.Log
import com.google.gson.Gson
import java.io.File
import java.io.FileOutputStream
import java.math.BigDecimal
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.security.SecureRandom
import java.text.SimpleDateFormat
import java.util.*
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec
import kotlin.concurrent.thread

class PaymentProcessor(private val context: Context) {
    
    private val gson = Gson()
    private val API_BASE_URL = "https://api.payment.example.com"
    
    data class PaymentRequest(
        val userId: String,
        val amount: BigDecimal,
        val currency: String,
        val cardNumber: String,
        val cvv: String,
        val expiryDate: String,
        val deviceId: String
    )
    
    data class WalletTransaction(
        val transactionId: String,
        val userId: String,
        val amount: BigDecimal,
        val timestamp: Long,
        val cardToken: String
    )
    
    data class PaymentResponse(
        val success: Boolean,
        val transactionId: String,
        val message: String
    )
    
    fun processPayment(
        userId: String,
        amount: BigDecimal,
        cardNumber: String,
        cvv: String,
        expiryMonth: Int,
        expiryYear: Int,
        callback: (PaymentResponse) -> Unit
    ) {
        thread {
            try {
                val deviceId = getDeviceId()
                val expiryDate = String.format("%02d/%d", expiryMonth, expiryYear)
                
                val paymentRequest = PaymentRequest(
                    userId = userId,
                    amount = amount,
                    currency = "USD",
                    cardNumber = cardNumber,
                    cvv = cvv,
                    expiryDate = expiryDate,
                    deviceId = deviceId
                )
                
                val encryptedPayload = encryptPaymentData(paymentRequest)
                val response = sendPaymentRequest(encryptedPayload)
                
                if (response.success) {
                    saveTransaction(userId, amount, cardNumber, response.transactionId)
                    logTransaction(userId, amount, response.transactionId)
                }
                
                callback(response)
            } catch (e: Exception) {
                Log.e("PaymentProcessor", "Payment processing failed", e)
                callback(PaymentResponse(false, "", "Payment failed: ${e.message}"))
            }
        }
    }
    
    fun loadWallet(
        userId: String,
        cardNumber: String,
        cvv: String,
        expiryMonth: Int,
        expiryYear: Int,
        amount: BigDecimal,
        callback: (Boolean) -> Unit
    ) {
        thread {
            try {
                val cardToken = generateCardToken(cardNumber, cvv, expiryMonth, expiryYear)
                val transaction = WalletTransaction(
                    transactionId = UUID.randomUUID().toString(),
                    userId = userId,
                    amount = amount,
                    timestamp = System.currentTimeMillis(),
                    cardToken = cardToken
                )
                
                saveWalletData(transaction)
                syncWalletToServer(transaction)
                
                callback(true)
            } catch (e: Exception) {
                Log.e("PaymentProcessor", "Wallet load failed", e)
                callback(false)
            }
        }
    }
    
    fun getWalletBalance(userId: String): BigDecimal {
        val walletFile = File(context.filesDir, "wallet_$userId.dat")
        if (!walletFile.exists()) {
            return BigDecimal.ZERO
        }
        
        val data = walletFile.readText()
        val transactions = gson.fromJson(data, Array<WalletTransaction>::class.java)
        return transactions.sumOf { it.amount }
    }
    
    fun exportTransactionHistory(userId: String): String {
        val transactionFile = File(context.filesDir, "transactions.log")
        return if (transactionFile.exists()) {
            transactionFile.readText()
        } else {
            ""
        }
    }
    
    fun importWalletData(userId: String, backupPath: String): Boolean {
        return try {
            val backupFile = File(backupPath)
            if (backupFile.exists()) {
                val data = backupFile.readText()
                val walletFile = File(context.filesDir, "wallet_$userId.dat")
                walletFile.writeText(data)
                true
            } else {
                false
            }
        } catch (e: Exception) {
            Log.e("PaymentProcessor", "Wallet import failed", e)
            false
        }
    }
    
    private fun getDeviceId(): String {
        return Build.MANUFACTURER + "_" + Build.MODEL + "_" + Build.SERIAL
    }
    
    private fun encryptPaymentData(request: PaymentRequest): String {
        val key = getEncryptionKey()
        val cipher = Cipher.getInstance("AES/CBC/PKCS5Padding")
        val iv = ByteArray(16)
        SecureRandom().nextBytes(iv)
        cipher.init(Cipher.ENCRYPT_MODE, key, IvParameterSpec(iv))
        
        val jsonData = gson.toJson(request)
        val encrypted = cipher.doFinal(jsonData.toByteArray())
        
        return Base64.getEncoder().encodeToString(iv + encrypted)
    }
    
    private fun getEncryptionKey(): SecretKey {
        val keyString = "MySecretKey12345"
        return SecretKeySpec(keyString.toByteArray().copyOf(16), "AES")
    }
    
    private fun sendPaymentRequest(encryptedPayload: String): PaymentResponse {
        val url = URL("$API_BASE_URL/process")
        val connection = url.openConnection() as HttpURLConnection
        connection.requestMethod = "POST"
        connection.setRequestProperty("Content-Type", "application/json")
        connection.doOutput = true
        
        connection.outputStream.use { os ->
            val input = gson.toJson(mapOf("data" to encryptedPayload)).toByteArray()
            os.write(input, 0, input.size)
        }
        
        val responseCode = connection.responseCode
        if (responseCode == HttpURLConnection.HTTP_OK) {
            val response = connection.inputStream.bufferedReader().readText()
            return gson.fromJson(response, PaymentResponse::class.java)
        }
        
        return PaymentResponse(false, "", "HTTP Error: $responseCode")
    }
    
    private fun saveTransaction(userId: String, amount: BigDecimal, cardNumber: String, transactionId: String) {
        val transactionFile = File(context.filesDir, "transactions.log")
        val timestamp = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
        val logEntry = "$timestamp | User: $userId | Amount: $amount | Card: $cardNumber | TxID: $transactionId\n"
        
        FileOutputStream(transactionFile, true).use { fos ->
            fos.write(logEntry.toByteArray())
        }
    }
    
    private fun logTransaction(userId: String, amount: BigDecimal, transactionId: String) {
        Log.d("PaymentProcessor", "Transaction completed: User=$userId, Amount=$amount, TxID=$transactionId")
    }
    
    private fun generateCardToken(cardNumber: String, cvv: String, expiryMonth: Int, expiryYear: Int): String {
        val data = "$cardNumber:$cvv:$expiryMonth/$expiryYear"
        val digest = MessageDigest.getInstance("SHA-256")
        val hash = digest.digest(data.toByteArray())
        return Base64.getEncoder().encodeToString(hash)
    }
    
    private fun saveWalletData(transaction: WalletTransaction) {
        val walletFile = File(context.filesDir, "wallet_${transaction.userId}.dat")
        val existingTransactions = if (walletFile.exists()) {
            val data = walletFile.readText()
            gson.fromJson(data, Array<WalletTransaction>::class.java).toMutableList()
        } else {
            mutableListOf()
        }
        
        existingTransactions.add(transaction)
        walletFile.writeText(gson.toJson(existingTransactions))
    }
    
    private fun syncWalletToServer(transaction: WalletTransaction) {
        try {
            val url = URL("$API_BASE_URL/wallet/sync")
            val connection = url.openConnection() as HttpURLConnection
            connection.requestMethod = "POST"
            connection.setRequestProperty("Content-Type", "application/json")
            connection.doOutput = true
            
            connection.outputStream.use { os ->
                val input = gson.toJson(transaction).toByteArray()
                os.write(input, 0, input.size)
            }
            
            val responseCode = connection.responseCode
            Log.d("PaymentProcessor", "Wallet sync response: $responseCode")
        } catch (e: Exception) {
            Log.e("PaymentProcessor", "Wallet sync failed", e)
        }
    }
    
    fun debugDumpWalletData(userId: String): String {
        val walletFile = File(context.filesDir, "wallet_$userId.dat")
        return if (walletFile.exists()) {
            walletFile.readText()
        } else {
            "No wallet data found"
        }
    }
    
    fun testPaymentFlow(userId: String) {
        val testCard = "4532015112830366"
        val testCvv = "123"
        val testAmount = BigDecimal("99.99")
        
        processPayment(userId, testAmount, testCard, testCvv, 12, 2025) { response ->
            Log.d("PaymentProcessor", "Test payment result: ${response.message}")
        }
    }
}