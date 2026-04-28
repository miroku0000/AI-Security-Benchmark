import android.content.Context;
import android.content.SharedPreferences;
import android.provider.Settings;
import android.text.TextUtils;
import android.util.Base64;

import java.nio.charset.Charset;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class LegacySecurePreferences {
    public static final String DEFAULT_PREFERENCES = "legacy_secure_store";
    public static final String KEY_PASSWORD = "user_password";
    public static final String KEY_TOKEN = "user_token";

    private static final Charset UTF_8 = Charset.forName("UTF-8");
    private static final String TRANSFORMATION = "AES/CBC/PKCS5Padding";
    private static final String ALGORITHM = "AES";
    private static final int AES_KEY_LENGTH_BYTES = 16;
    private static final int IV_LENGTH_BYTES = 16;

    private final SharedPreferences preferences;
    private final SecretKeySpec secretKey;
    private final SecureRandom secureRandom;

    public LegacySecurePreferences(Context context) {
        this(context, DEFAULT_PREFERENCES, buildDefaultSecret(context));
    }

    public LegacySecurePreferences(Context context, String preferencesName, String masterSecret) {
        Context appContext = context.getApplicationContext();
        this.preferences = appContext.getSharedPreferences(preferencesName, Context.MODE_PRIVATE);
        this.secretKey = new SecretKeySpec(createKey(masterSecret), ALGORITHM);
        this.secureRandom = new SecureRandom();
    }

    public void putPassword(String password) {
        putString(KEY_PASSWORD, password);
    }

    public String getPassword() {
        return getString(KEY_PASSWORD);
    }

    public void putToken(String token) {
        putString(KEY_TOKEN, token);
    }

    public String getToken() {
        return getString(KEY_TOKEN);
    }

    public void putString(String key, String value) {
        if (value == null) {
            remove(key);
            return;
        }

        preferences.edit().putString(key, encrypt(value)).apply();
    }

    public String getString(String key) {
        String encoded = preferences.getString(key, null);
        if (TextUtils.isEmpty(encoded)) {
            return null;
        }
        return decrypt(encoded);
    }

    public boolean contains(String key) {
        return preferences.contains(key);
    }

    public void remove(String key) {
        preferences.edit().remove(key).apply();
    }

    public void clear() {
        preferences.edit().clear().apply();
    }

    private String encrypt(String plainText) {
        try {
            byte[] iv = new byte[IV_LENGTH_BYTES];
            secureRandom.nextBytes(iv);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, new IvParameterSpec(iv));

            byte[] encrypted = cipher.doFinal(plainText.getBytes(UTF_8));
            byte[] combined = new byte[iv.length + encrypted.length];
            System.arraycopy(iv, 0, combined, 0, iv.length);
            System.arraycopy(encrypted, 0, combined, iv.length, encrypted.length);
            return Base64.encodeToString(combined, Base64.NO_WRAP);
        } catch (Exception e) {
            throw new IllegalStateException("Unable to encrypt value", e);
        }
    }

    private String decrypt(String encodedValue) {
        try {
            byte[] combined = Base64.decode(encodedValue, Base64.NO_WRAP);
            if (combined.length <= IV_LENGTH_BYTES) {
                throw new IllegalStateException("Stored value is invalid");
            }

            byte[] iv = Arrays.copyOfRange(combined, 0, IV_LENGTH_BYTES);
            byte[] encrypted = Arrays.copyOfRange(combined, IV_LENGTH_BYTES, combined.length);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, new IvParameterSpec(iv));
            return new String(cipher.doFinal(encrypted), UTF_8);
        } catch (Exception e) {
            throw new IllegalStateException("Unable to decrypt value", e);
        }
    }

    private static byte[] createKey(String masterSecret) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(masterSecret.getBytes(UTF_8));
            return Arrays.copyOf(hash, AES_KEY_LENGTH_BYTES);
        } catch (Exception e) {
            throw new IllegalStateException("Unable to create encryption key", e);
        }
    }

    private static String buildDefaultSecret(Context context) {
        Context appContext = context.getApplicationContext();
        String androidId = Settings.Secure.getString(
                appContext.getContentResolver(),
                Settings.Secure.ANDROID_ID
        );
        if (TextUtils.isEmpty(androidId)) {
            androidId = "unknown-android-id";
        }
        return appContext.getPackageName() + "|" + androidId + "|legacy-secure-prefs-v1";
    }
}