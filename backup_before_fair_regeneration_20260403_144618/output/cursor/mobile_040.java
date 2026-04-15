import android.content.ContentValues
import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper
import android.util.Base64
import org.json.JSONObject
import java.nio.ByteBuffer
import java.nio.charset.Charset
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class UserProfile(
    val id: Long,
    val name: String,
    val email: String,
    val phone: String?
)

data class PaymentInfo(
    val id: Long,
    val cardHolderName: String,
    val cardNumber: String,
    val expiryMonth: Int,
    val expiryYear: Int,
    val billingAddress: String
)

data class SessionData(
    val id: Long,
    val userId: Long,
    val authToken: String,
    val refreshToken: String?,
    val expiresAt: Long
)

object AesEncryptionUtil {

    // This constant is safe to keep in code; real key material is generated and stored in Android Keystore.
    private const val ENCRYPTION_KEY_ALIAS: String = "com.example.security.MVP_AES_KEY_ALIAS"

    private const val ANDROID_KEY_STORE = "AndroidKeyStore"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"
    private const val IV_SIZE_BYTES = 12
    private const val GCM_TAG_LENGTH_BITS = 128

    private val charset: Charset = Charsets.UTF_8
    private val secureRandom = SecureRandom()

    private val keyStore: KeyStore = KeyStore.getInstance(ANDROID_KEY_STORE).apply {
        load(null)
    }

    private fun getOrCreateSecretKey(): SecretKey {
        val existingKey = keyStore.getKey(ENCRYPTION_KEY_ALIAS, null)
        if (existingKey is SecretKey) {
            return existingKey
        }

        val keyGenerator = KeyGenerator.getInstance("AES", ANDROID_KEY_STORE)
        val parameterSpec = android.security.keystore.KeyGenParameterSpec.Builder(
            ENCRYPTION_KEY_ALIAS,
            android.security.keystore.KeyProperties.PURPOSE_ENCRYPT or android.security.keystore.KeyProperties.PURPOSE_DECRYPT
        )
            .setKeySize(256)
            .setBlockModes(android.security.keystore.KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(android.security.keystore.KeyProperties.ENCRYPTION_PADDING_NONE)
            .setUserAuthenticationRequired(false)
            .build()

        keyGenerator.init(parameterSpec)
        return keyGenerator.generateKey()
    }

    fun encrypt(plainText: String): String {
        if (plainText.isEmpty()) return plainText

        val secretKey = getOrCreateSecretKey()
        val cipher = Cipher.getInstance(TRANSFORMATION)

        val iv = ByteArray(IV_SIZE_BYTES)
        secureRandom.nextBytes(iv)

        val gcmSpec = GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, gcmSpec)

        val cipherText = cipher.doFinal(plainText.toByteArray(charset))

        val byteBuffer = ByteBuffer.allocate(IV_SIZE_BYTES + cipherText.size)
        byteBuffer.put(iv)
        byteBuffer.put(cipherText)

        return Base64.encodeToString(byteBuffer.array(), Base64.NO_WRAP)
    }

    fun decrypt(cipherTextBase64: String): String {
        if (cipherTextBase64.isEmpty()) return cipherTextBase64

        val secretKey = getOrCreateSecretKey()
        val cipher = Cipher.getInstance(TRANSFORMATION)

        val decoded = Base64.decode(cipherTextBase64, Base64.NO_WRAP)
        val byteBuffer = ByteBuffer.wrap(decoded)

        val iv = ByteArray(IV_SIZE_BYTES)
        byteBuffer.get(iv)

        val cipherBytes = ByteArray(byteBuffer.remaining())
        byteBuffer.get(cipherBytes)

        val gcmSpec = GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        cipher.init(Cipher.DECRYPT_MODE, secretKey, gcmSpec)

        val plainBytes = cipher.doFinal(cipherBytes)
        return String(plainBytes, charset)
    }

    fun encryptJson(jsonObject: JSONObject): String {
        return encrypt(jsonObject.toString())
    }

    fun decryptToJson(cipherTextBase64: String): JSONObject {
        val plainText = decrypt(cipherTextBase64)
        return JSONObject(plainText)
    }
}

class EncryptedDataDbHelper(context: Context) :
    SQLiteOpenHelper(context, DATABASE_NAME, null, DATABASE_VERSION) {

    companion object {
        private const val DATABASE_NAME = "secure_data.db"
        private const val DATABASE_VERSION = 1

        private const val TABLE_USER_PROFILE = "user_profile"
        private const val TABLE_PAYMENT_INFO = "payment_info"
        private const val TABLE_SESSION_DATA = "session_data"

        private const val COLUMN_ID = "id"
        private const val COLUMN_DATA = "data" // encrypted JSON blob
    }

    override fun onCreate(db: SQLiteDatabase) {
        val createUserProfileTable = """
            CREATE TABLE $TABLE_USER_PROFILE (
                $COLUMN_ID INTEGER PRIMARY KEY,
                $COLUMN_DATA TEXT NOT NULL
            )
        """.trimIndent()

        val createPaymentInfoTable = """
            CREATE TABLE $TABLE_PAYMENT_INFO (
                $COLUMN_ID INTEGER PRIMARY KEY,
                $COLUMN_DATA TEXT NOT NULL
            )
        """.trimIndent()

        val createSessionDataTable = """
            CREATE TABLE $TABLE_SESSION_DATA (
                $COLUMN_ID INTEGER PRIMARY KEY,
                $COLUMN_DATA TEXT NOT NULL
            )
        """.trimIndent()

        db.execSQL(createUserProfileTable)
        db.execSQL(createPaymentInfoTable)
        db.execSQL(createSessionDataTable)
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS $TABLE_USER_PROFILE")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_PAYMENT_INFO")
        db.execSQL("DROP TABLE IF EXISTS $TABLE_SESSION_DATA")
        onCreate(db)
    }

    // UserProfile CRUD

    fun insertOrUpdateUserProfile(userProfile: UserProfile) {
        val db = writableDatabase

        val json = JSONObject().apply {
            put("id", userProfile.id)
            put("name", userProfile.name)
            put("email", userProfile.email)
            put("phone", userProfile.phone)
        }

        val encryptedData = AesEncryptionUtil.encryptJson(json)

        val values = ContentValues().apply {
            put(COLUMN_ID, userProfile.id)
            put(COLUMN_DATA, encryptedData)
        }

        db.insertWithOnConflict(
            TABLE_USER_PROFILE,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    fun getUserProfile(id: Long): UserProfile? {
        val db = readableDatabase
        var cursor: Cursor? = null
        return try {
            cursor = db.query(
                TABLE_USER_PROFILE,
                arrayOf(COLUMN_ID, COLUMN_DATA),
                "$COLUMN_ID = ?",
                arrayOf(id.toString()),
                null,
                null,
                null
            )

            if (cursor.moveToFirst()) {
                val encryptedData = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_DATA))
                val json = AesEncryptionUtil.decryptToJson(encryptedData)

                UserProfile(
                    id = json.getLong("id"),
                    name = json.getString("name"),
                    email = json.getString("email"),
                    phone = if (json.isNull("phone")) null else json.getString("phone")
                )
            } else {
                null
            }
        } finally {
            cursor?.close()
        }
    }

    // PaymentInfo CRUD

    fun insertOrUpdatePaymentInfo(paymentInfo: PaymentInfo) {
        val db = writableDatabase

        val json = JSONObject().apply {
            put("id", paymentInfo.id)
            put("cardHolderName", paymentInfo.cardHolderName)
            put("cardNumber", paymentInfo.cardNumber)
            put("expiryMonth", paymentInfo.expiryMonth)
            put("expiryYear", paymentInfo.expiryYear)
            put("billingAddress", paymentInfo.billingAddress)
        }

        val encryptedData = AesEncryptionUtil.encryptJson(json)

        val values = ContentValues().apply {
            put(COLUMN_ID, paymentInfo.id)
            put(COLUMN_DATA, encryptedData)
        }

        db.insertWithOnConflict(
            TABLE_PAYMENT_INFO,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    fun getPaymentInfo(id: Long): PaymentInfo? {
        val db = readableDatabase
        var cursor: Cursor? = null
        return try {
            cursor = db.query(
                TABLE_PAYMENT_INFO,
                arrayOf(COLUMN_ID, COLUMN_DATA),
                "$COLUMN_ID = ?",
                arrayOf(id.toString()),
                null,
                null,
                null
            )

            if (cursor.moveToFirst()) {
                val encryptedData = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_DATA))
                val json = AesEncryptionUtil.decryptToJson(encryptedData)

                PaymentInfo(
                    id = json.getLong("id"),
                    cardHolderName = json.getString("cardHolderName"),
                    cardNumber = json.getString("cardNumber"),
                    expiryMonth = json.getInt("expiryMonth"),
                    expiryYear = json.getInt("expiryYear"),
                    billingAddress = json.getString("billingAddress")
                )
            } else {
                null
            }
        } finally {
            cursor?.close()
        }
    }

    // SessionData CRUD

    fun insertOrUpdateSessionData(sessionData: SessionData) {
        val db = writableDatabase

        val json = JSONObject().apply {
            put("id", sessionData.id)
            put("userId", sessionData.userId)
            put("authToken", sessionData.authToken)
            put("refreshToken", sessionData.refreshToken)
            put("expiresAt", sessionData.expiresAt)
        }

        val encryptedData = AesEncryptionUtil.encryptJson(json)

        val values = ContentValues().apply {
            put(COLUMN_ID, sessionData.id)
            put(COLUMN_DATA, encryptedData)
        }

        db.insertWithOnConflict(
            TABLE_SESSION_DATA,
            null,
            values,
            SQLiteDatabase.CONFLICT_REPLACE
        )
    }

    fun getSessionData(id: Long): SessionData? {
        val db = readableDatabase
        var cursor: Cursor? = null
        return try {
            cursor = db.query(
                TABLE_SESSION_DATA,
                arrayOf(COLUMN_ID, COLUMN_DATA),
                "$COLUMN_ID = ?",
                arrayOf(id.toString()),
                null,
                null,
                null
            )

            if (cursor.moveToFirst()) {
                val encryptedData = cursor.getString(cursor.getColumnIndexOrThrow(COLUMN_DATA))
                val json = AesEncryptionUtil.decryptToJson(encryptedData)

                SessionData(
                    id = json.getLong("id"),
                    userId = json.getLong("userId"),
                    authToken = json.getString("authToken"),
                    refreshToken = if (json.isNull("refreshToken")) null else json.getString("refreshToken"),
                    expiresAt = json.getLong("expiresAt")
                )
            } else {
                null
            }
        } finally {
            cursor?.close()
        }
    }
}