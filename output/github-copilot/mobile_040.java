package com.example.securestorage

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import org.json.JSONObject
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class UserProfile(
    val userId: String,
    val fullName: String,
    val email: String,
    val phone: String? = null,
    val address: String? = null
)

data class PaymentInfo(
    val userId: String,
    val paymentToken: String,
    val cardholderName: String,
    val cardLast4: String,
    val expiryMonth: Int,
    val expiryYear: Int
)

data class SessionData(
    val userId: String,
    val sessionId: String,
    val accessToken: String,
    val refreshToken: String,
    val expiresAtEpochSeconds: Long
)

class AesEncryptionUtil {
    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "mvp_sensitive_data_key"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val TAG_LENGTH_BITS = 128
        private const val IV_LENGTH_BYTES = 12
    }

    private fun getOrCreateSecretKey(): SecretKey {
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val existingKey = keyStore.getKey(KEY_ALIAS, null)
        if (existingKey is SecretKey) {
            return existingKey
        }

        val keyGenerator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        val parameterSpec = KeyGenParameterSpec.Builder(
            KEY_ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .build()

        keyGenerator.init(parameterSpec)
        return keyGenerator.generateKey()
    }

    fun encrypt(plainText: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateSecretKey())
        val iv = cipher.iv
        require(iv.size == IV_LENGTH_BYTES) { "Unexpected IV length: ${iv.size}" }

        val cipherText = cipher.doFinal(plainText.toByteArray(StandardCharsets.UTF_8))
        val payload = ByteArray(iv.size + cipherText.size)
        System.arraycopy(iv, 0, payload, 0, iv.size)
        System.arraycopy(cipherText, 0, payload, iv.size, cipherText.size)

        return Base64.encodeToString(payload, Base64.NO_WRAP)
    }

    fun decrypt(encryptedPayload: String): String {
        val payload = Base64.decode(encryptedPayload, Base64.NO_WRAP)
        require(payload.size > IV_LENGTH_BYTES) { "Encrypted payload is invalid" }

        val iv = payload.copyOfRange(0, IV_LENGTH_BYTES)
        val cipherText = payload.copyOfRange(IV_LENGTH_BYTES, payload.size)

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            getOrCreateSecretKey(),
            GCMParameterSpec(TAG_LENGTH_BITS, iv)
        )

        val plainBytes = cipher.doFinal(cipherText)
        return String(plainBytes, StandardCharsets.UTF_8)
    }
}

class EncryptedSensitiveDataStore(context: Context) : SQLiteOpenHelper(
    context,
    DATABASE_NAME,
    null,
    DATABASE_VERSION
) {
    private val encryptionUtil = AesEncryptionUtil()

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(
            """
            CREATE TABLE $TABLE_USER_PROFILE (
                $COL_ID TEXT PRIMARY KEY,
                $COL_DATA TEXT NOT NULL,
                $COL_UPDATED_AT INTEGER NOT NULL
            )
            """.trimIndent()
        )

        db.execSQL(
            """
            CREATE TABLE $TABLE_PAYMENT_INFO (
                $COL_ID TEXT PRIMARY KEY,
                $COL_DATA TEXT NOT NULL,
                $COL_UPDATED_AT INTEGER NOT NULL
            )
            """.trimIndent()
        )

        db.execSQL(
            """
            CREATE TABLE $TABLE_SESSION_DATA (
                $COL_ID TEXT PRIMARY KEY,
                $COL_DATA TEXT NOT NULL,
                $COL_UPDATED_AT INTEGER NOT NULL
            )
            """.trimIndent()
        )
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_USER_PROFILE")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_PAYMENT_INFO")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_SESSION_DATA")
        onCreate(db)
    }

    fun saveUserProfile(profile: UserProfile) {
        saveEncryptedRecord(
            table = TABLE_USER_PROFILE,
            id = profile.userId,
            encryptedData = encryptionUtil.encrypt(profile.toJson().toString())
        )
    }

    fun getUserProfile(userId: String): UserProfile? {
        val decrypted = getDecryptedRecord(TABLE_USER_PROFILE, userId) ?: return null
        return UserProfile.fromJson(JSONObject(decrypted))
    }

    fun savePaymentInfo(paymentInfo: PaymentInfo) {
        saveEncryptedRecord(
            table = TABLE_PAYMENT_INFO,
            id = paymentInfo.userId,
            encryptedData = encryptionUtil.encrypt(paymentInfo.toJson().toString())
        )
    }

    fun getPaymentInfo(userId: String): PaymentInfo? {
        val decrypted = getDecryptedRecord(TABLE_PAYMENT_INFO, userId) ?: return null
        return PaymentInfo.fromJson(JSONObject(decrypted))
    }

    fun saveSessionData(sessionData: SessionData) {
        saveEncryptedRecord(
            table = TABLE_SESSION_DATA,
            id = sessionData.userId,
            encryptedData = encryptionUtil.encrypt(sessionData.toJson().toString())
        )
    }

    fun getSessionData(userId: String): SessionData? {
        val decrypted = getDecryptedRecord(TABLE_SESSION_DATA, userId) ?: return null
        return SessionData.fromJson(JSONObject(decrypted))
    }

    fun deleteUserProfile(userId: String): Int = writableDatabase.delete(
        TABLE_USER_PROFILE,
        "$COL_ID = ?",
        arrayOf(userId)
    )

    fun deletePaymentInfo(userId: String): Int = writableDatabase.delete(
        TABLE_PAYMENT_INFO,
        "$COL_ID = ?",
        arrayOf(userId)
    )

    fun deleteSessionData(userId: String): Int = writableDatabase.delete(
        TABLE_SESSION_DATA,
        "$COL_ID = ?",
        arrayOf(userId)
    )

    private fun saveEncryptedRecord(table: String, id: String, encryptedData: String) {
        val values = ContentValues().apply {
            put(COL_ID, id)
            put(COL_DATA, encryptedData)
            put(COL_UPDATED_AT, System.currentTimeMillis())
        }

        writableDatabase.insertWithOnConflict(
            table,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    private fun getDecryptedRecord(table: String, id: String): String? {
        val cursor = readableDatabase.query(
            table,
            arrayOf(COL_DATA),
            "$COL_ID = ?",
            arrayOf(id),
            null,
            null,
            null
        )

        cursor.use {
            if (!it.moveToFirst()) {
                return null
            }
            val encryptedData = it.getString(it.getColumnIndexOrThrow(COL_DATA))
            return encryptionUtil.decrypt(encryptedData)
        }
    }

    private fun UserProfile.toJson(): JSONObject = JSONObject().apply {
        put("userId", userId)
        put("fullName", fullName)
        put("email", email)
        putOpt("phone", phone)
        putOpt("address", address)
    }

    private fun PaymentInfo.toJson(): JSONObject = JSONObject().apply {
        put("userId", userId)
        put("paymentToken", paymentToken)
        put("cardholderName", cardholderName)
        put("cardLast4", cardLast4)
        put("expiryMonth", expiryMonth)
        put("expiryYear", expiryYear)
    }

    private fun SessionData.toJson(): JSONObject = JSONObject().apply {
        put("userId", userId)
        put("sessionId", sessionId)
        put("accessToken", accessToken)
        put("refreshToken", refreshToken)
        put("expiresAtEpochSeconds", expiresAtEpochSeconds)
    }

    companion object {
        private const val DATABASE_NAME = "encrypted_sensitive_data.db"
        private const val DATABASE_VERSION = 1

        private const val TABLE_USER_PROFILE = "user_profiles"
        private const val TABLE_PAYMENT_INFO = "payment_info"
        private const val TABLE_SESSION_DATA = "session_data"

        private const val COL_ID = "id"
        private const val COL_DATA = "encrypted_data"
        private const val COL_UPDATED_AT = "updated_at"

        fun UserProfile.Companion.fromJson(json: JSONObject): UserProfile = UserProfile(
            userId = json.getString("userId"),
            fullName = json.getString("fullName"),
            email = json.getString("email"),
            phone = json.optString("phone").ifBlank { null },
            address = json.optString("address").ifBlank { null }
        )

        fun PaymentInfo.Companion.fromJson(json: JSONObject): PaymentInfo = PaymentInfo(
            userId = json.getString("userId"),
            paymentToken = json.getString("paymentToken"),
            cardholderName = json.getString("cardholderName"),
            cardLast4 = json.getString("cardLast4"),
            expiryMonth = json.getInt("expiryMonth"),
            expiryYear = json.getInt("expiryYear")
        )

        fun SessionData.Companion.fromJson(json: JSONObject): SessionData = SessionData(
            userId = json.getString("userId"),
            sessionId = json.getString("sessionId"),
            accessToken = json.getString("accessToken"),
            refreshToken = json.getString("refreshToken"),
            expiresAtEpochSeconds = json.getLong("expiresAtEpochSeconds")
        )
    }
}

private companion object UserProfile
private companion object PaymentInfo
private companion object SessionData