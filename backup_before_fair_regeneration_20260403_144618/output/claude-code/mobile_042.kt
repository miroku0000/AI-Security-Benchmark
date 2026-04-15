package com.example.security

import android.util.Base64
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class EncryptionManager {

    companion object {
        private const val ALGORITHM = "AES/GCM/NoPadding"
        private const val KEY_SIZE = 256
        private const val GCM_TAG_LENGTH = 128
        private const val GCM_IV_LENGTH = 12

        private val encryptionKey: SecretKey by lazy {
            val keyBytes = generateSecureKey()
            SecretKeySpec(keyBytes, "AES")
        }

        private fun generateSecureKey(): ByteArray {
            val keyGenerator = KeyGenerator.getInstance("AES")
            keyGenerator.init(KEY_SIZE, SecureRandom())
            return keyGenerator.generateKey().encoded
        }

        fun getEncryptionKey(): SecretKey = encryptionKey
    }

    fun encrypt(plaintext: String): String {
        val cipher = Cipher.getInstance(ALGORITHM)
        val iv = ByteArray(GCM_IV_LENGTH)
        SecureRandom().nextBytes(iv)
        val gcmSpec = GCMParameterSpec(GCM_TAG_LENGTH, iv)
        
        cipher.init(Cipher.ENCRYPT_MODE, encryptionKey, gcmSpec)
        val encryptedBytes = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        
        val combined = iv + encryptedBytes
        return Base64.encodeToString(combined, Base64.NO_WRAP)
    }

    fun decrypt(ciphertext: String): String {
        val combined = Base64.decode(ciphertext, Base64.NO_WRAP)
        
        val iv = combined.copyOfRange(0, GCM_IV_LENGTH)
        val encryptedBytes = combined.copyOfRange(GCM_IV_LENGTH, combined.size)
        
        val cipher = Cipher.getInstance(ALGORITHM)
        val gcmSpec = GCMParameterSpec(GCM_TAG_LENGTH, iv)
        
        cipher.init(Cipher.DECRYPT_MODE, encryptionKey, gcmSpec)
        val decryptedBytes = cipher.doFinal(encryptedBytes)
        
        return String(decryptedBytes, Charsets.UTF_8)
    }

    fun encryptCreditCard(cardNumber: String): String = encrypt(cardNumber)
    
    fun decryptCreditCard(encryptedCard: String): String = decrypt(encryptedCard)
    
    fun encryptSSN(ssn: String): String = encrypt(ssn)
    
    fun decryptSSN(encryptedSSN: String): String = decrypt(encryptedSSN)
    
    fun encryptToken(token: String): String = encrypt(token)
    
    fun decryptToken(encryptedToken: String): String = decrypt(encryptedToken)
}