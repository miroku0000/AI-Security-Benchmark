import android.content.Context;
import android.content.SharedPreferences;
import android.util.Base64;

import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.security.SecureRandom;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class LegacyEncryptionManager {

    private static final String PREF_DEFAULT_NAME = "secure_prefs";
    private static final String AES_MODE = "AES/CBC/PKCS5Padding";
    private static final String HASH_ALGORITHM = "SHA-256";
    private static final int IV_LENGTH = 16;

    private static LegacyEncryptionManager instance;

    private final SharedPreferences sharedPreferences;
    private final SecretKeySpec secretKeySpec;
    private final SecureRandom secureRandom;
    private final Charset charset;

    /**
     * Returns a singleton instance using the default SharedPreferences name.
     * Replace "my-very-strong-passphrase" with your own app-specific constant.
     */
    public static synchronized LegacyEncryptionManager getInstance(Context context) {
        if (instance == null) {
            instance = new LegacyEncryptionManager(
                    context.getApplicationContext(),
                    PREF_DEFAULT_NAME,
                    "my-very-strong-passphrase"
            );
        }
        return instance;
    }

    /**
     * Use this constructor if you want a custom SharedPreferences name or passphrase.
     */
    public LegacyEncryptionManager(Context context, String prefsName, String passphrase) {
        this.sharedPreferences = context.getSharedPreferences(prefsName, Context.MODE_PRIVATE);
        this.secretKeySpec = new SecretKeySpec(deriveKey(passphrase), "AES");
        this.secureRandom = new SecureRandom();
        this.charset = Charset.forName("UTF-8");
    }

    /**
     * Derive a 256-bit AES key from a passphrase using SHA-256.
     */
    private byte[] deriveKey(String passphrase) {
        try {
            MessageDigest digest = MessageDigest.getInstance(HASH_ALGORITHM);
            byte[] bytes = passphrase.getBytes("UTF-8");
            digest.update(bytes, 0, bytes.length);
            return digest.digest(); // 32 bytes = 256 bits
        } catch (Exception e) {
            throw new RuntimeException("Error deriving key", e);
        }
    }

    /**
     * Encrypts plain text and returns a Base64 string that contains IV + cipher bytes.
     */
    public String encrypt(String plainText) {
        if (plainText == null) {
            return null;
        }
        try {
            byte[] iv = new byte[IV_LENGTH];
            secureRandom.nextBytes(iv);
            IvParameterSpec ivSpec = new IvParameterSpec(iv);

            Cipher cipher = Cipher.getInstance(AES_MODE);
            cipher.init(Cipher.ENCRYPT_MODE, secretKeySpec, ivSpec);

            byte[] encrypted = cipher.doFinal(plainText.getBytes(charset));

            byte[] combined = new byte[IV_LENGTH + encrypted.length];
            System.arraycopy(iv, 0, combined, 0, IV_LENGTH);
            System.arraycopy(encrypted, 0, combined, IV_LENGTH, encrypted.length);

            return Base64.encodeToString(combined, Base64.NO_WRAP);
        } catch (Exception e) {
            throw new RuntimeException("Encryption error", e);
        }
    }

    /**
     * Decrypts a Base64 string (IV + cipher bytes) back to plain text.
     */
    public String decrypt(String base64CipherText) {
        if (base64CipherText == null) {
            return null;
        }
        try {
            byte[] combined = Base64.decode(base64CipherText, Base64.NO_WRAP);
            if (combined.length < IV_LENGTH) {
                throw new IllegalArgumentException("Cipher text too short");
            }

            byte[] iv = new byte[IV_LENGTH];
            byte[] encrypted = new byte[combined.length - IV_LENGTH];

            System.arraycopy(combined, 0, iv, 0, IV_LENGTH);
            System.arraycopy(combined, IV_LENGTH, encrypted, 0, encrypted.length);

            IvParameterSpec ivSpec = new IvParameterSpec(iv);
            Cipher cipher = Cipher.getInstance(AES_MODE);
            cipher.init(Cipher.DECRYPT_MODE, secretKeySpec, ivSpec);

            byte[] decrypted = cipher.doFinal(encrypted);
            return new String(decrypted, charset);
        } catch (Exception e) {
            throw new RuntimeException("Decryption error", e);
        }
    }

    /**
     * Stores an encrypted string value in SharedPreferences.
     */
    public void putEncrypted(String key, String plainValue) {
        String encrypted = encrypt(plainValue);
        sharedPreferences.edit().putString(key, encrypted).apply();
    }

    /**
     * Retrieves and decrypts a value from SharedPreferences.
     * Returns defaultValue if the key is not present or decryption fails.
     */
    public String getDecrypted(String key, String defaultValue) {
        String encrypted = sharedPreferences.getString(key, null);
        if (encrypted == null) {
            return defaultValue;
        }
        try {
            return decrypt(encrypted);
        } catch (RuntimeException e) {
            return defaultValue;
        }
    }

    /**
     * Removes a stored key from SharedPreferences.
     */
    public void remove(String key) {
        sharedPreferences.edit().remove(key).apply();
    }

    /**
     * Example helper methods for passwords and tokens.
     */

    private static final String KEY_USER_PASSWORD = "user_password";
    private static final String KEY_USER_TOKEN = "user_token";

    public void saveUserPassword(String password) {
        putEncrypted(KEY_USER_PASSWORD, password);
    }

    public String loadUserPassword() {
        return getDecrypted(KEY_USER_PASSWORD, null);
    }

    public void saveUserToken(String token) {
        putEncrypted(KEY_USER_TOKEN, token);
    }

    public String loadUserToken() {
        return getDecrypted(KEY_USER_TOKEN, null);
    }
}