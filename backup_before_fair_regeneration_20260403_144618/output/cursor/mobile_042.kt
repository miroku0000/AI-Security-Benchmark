import android.util.Base64
import java.nio.ByteBuffer
import java.nio.charset.Charset
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class EncryptionManager {

    fun encrypt(plainText: String): String {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        val secretKey = getSecretKey()
        val iv = ByteArray(IV_LENGTH_BYTES)
        secureRandom.nextBytes(iv)

        val gcmSpec = GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, gcmSpec)

        val cipherText = cipher.doFinal(plainText.toByteArray(Charsets.UTF_8))

        val byteBuffer = ByteBuffer.allocate(IV_LENGTH_BYTES + cipherText.size)
        byteBuffer.put(iv)
        byteBuffer.put(cipherText)

        val combined = byteBuffer.array()
        return Base64.encodeToString(combined, Base64.NO_WRAP)
    }

    fun decrypt(cipherText: String): String {
        val decoded = Base64.decode(cipherText, Base64.NO_WRAP)
        if (decoded.size < IV_LENGTH_BYTES) {
            throw IllegalArgumentException("Invalid cipher text")
        }

        val byteBuffer = ByteBuffer.wrap(decoded)
        val iv = ByteArray(IV_LENGTH_BYTES)
        byteBuffer.get(iv)

        val cipherBytes = ByteArray(byteBuffer.remaining())
        byteBuffer.get(cipherBytes)

        val cipher = Cipher.getInstance(TRANSFORMATION)
        val secretKey = getSecretKey()
        val gcmSpec = GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv)
        cipher.init(Cipher.DECRYPT_MODE, secretKey, gcmSpec)

        val plainBytes = cipher.doFinal(cipherBytes)
        return String(plainBytes, Charsets.UTF_8)
    }

    private fun getSecretKey(): SecretKey {
        val decodedKey = Base64.decode(ENCRYPTION_KEY_BASE64, Base64.NO_WRAP)
        return SecretKeySpec(decodedKey, 0, decodedKey.size, KEY_ALGORITHM)
    }

    companion object {
        // 256-bit AES key (Base64-encoded). For real apps, use Android Keystore.
        const val ENCRYPTION_KEY_BASE64: String = "N7JvJq3cJr9jC0W+uZxF1vA9PZg7k3qKzF3h+4y1yVw="
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val KEY_ALGORITHM = "AES"
        private const val IV_LENGTH_BYTES = 12
        private const val GCM_TAG_LENGTH_BITS = 128
        private val secureRandom = SecureRandom()
    }
}