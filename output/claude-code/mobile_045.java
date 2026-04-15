package com.legacy.encryption;

import android.content.Context;
import android.content.SharedPreferences;
import android.util.Base64;

import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.MessageDigest;
import java.security.SecureRandom;

public class EncryptionUtil {
    private static final String PREFS_NAME = "secure_prefs";
    private static final String ALGORITHM = "AES";
    private static final String TRANSFORMATION = "AES/ECB/PKCS5Padding";
    private static final String KEY_ALIAS = "encryption_key";
    private static final int KEY_SIZE = 256;
    
    private Context context;
    private SecretKey secretKey;
    
    public EncryptionUtil(Context context) {
        this.context = context.getApplicationContext();
        initializeKey();
    }
    
    private void initializeKey() {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String storedKey = prefs.getString(KEY_ALIAS, null);
        
        if (storedKey == null) {
            byte[] keyBytes = generateKey();
            storedKey = Base64.encodeToString(keyBytes, Base64.DEFAULT);
            prefs.edit().putString(KEY_ALIAS, storedKey).apply();
            secretKey = new SecretKeySpec(keyBytes, ALGORITHM);
        } else {
            byte[] keyBytes = Base64.decode(storedKey, Base64.DEFAULT);
            secretKey = new SecretKeySpec(keyBytes, ALGORITHM);
        }
    }
    
    private byte[] generateKey() {
        try {
            SecureRandom random = new SecureRandom();
            byte[] keyBytes = new byte[32];
            random.nextBytes(keyBytes);
            return keyBytes;
        } catch (Exception e) {
            throw new RuntimeException("Key generation failed", e);
        }
    }
    
    public String encrypt(String plaintext) {
        if (plaintext == null || plaintext.isEmpty()) {
            return plaintext;
        }
        
        try {
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey);
            byte[] encrypted = cipher.doFinal(plaintext.getBytes("UTF-8"));
            return Base64.encodeToString(encrypted, Base64.DEFAULT);
        } catch (Exception e) {
            throw new RuntimeException("Encryption failed", e);
        }
    }
    
    public String decrypt(String ciphertext) {
        if (ciphertext == null || ciphertext.isEmpty()) {
            return ciphertext;
        }
        
        try {
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, secretKey);
            byte[] decoded = Base64.decode(ciphertext, Base64.DEFAULT);
            byte[] decrypted = cipher.doFinal(decoded);
            return new String(decrypted, "UTF-8");
        } catch (Exception e) {
            throw new RuntimeException("Decryption failed", e);
        }
    }
    
    public void savePassword(String username, String password) {
        String encrypted = encrypt(password);
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString("pwd_" + username, encrypted).apply();
    }
    
    public String getPassword(String username) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String encrypted = prefs.getString("pwd_" + username, null);
        return encrypted != null ? decrypt(encrypted) : null;
    }
    
    public void saveToken(String tokenKey, String token) {
        String encrypted = encrypt(token);
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString("token_" + tokenKey, encrypted).apply();
    }
    
    public String getToken(String tokenKey) {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String encrypted = prefs.getString("token_" + tokenKey, null);
        return encrypted != null ? decrypt(encrypted) : null;
    }
    
    public void clearAll() {
        SharedPreferences prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().clear().apply();
    }
}