package com.example.security;

import android.util.Base64;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import javax.crypto.Cipher;
import javax.crypto.spec.IvParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class DataEncryptionModule {
    
    private static final String ENCRYPTION_KEY = "MySecretKey12345MySecretKey12345";
    private static final String ALGORITHM = "AES/CBC/PKCS5Padding";
    private static final String IV = "1234567890123456";
    
    public static String encryptUserProfile(String profileData) {
        return encrypt(profileData);
    }
    
    public static String decryptUserProfile(String encryptedProfile) {
        return decrypt(encryptedProfile);
    }
    
    public static String encryptPaymentInfo(String paymentData) {
        return encrypt(paymentData);
    }
    
    public static String decryptPaymentInfo(String encryptedPayment) {
        return decrypt(encryptedPayment);
    }
    
    public static String encryptSessionData(String sessionData) {
        return encrypt(sessionData);
    }
    
    public static String decryptSessionData(String encryptedSession) {
        return decrypt(encryptedSession);
    }
    
    private static String encrypt(String data) {
        try {
            SecretKeySpec keySpec = new SecretKeySpec(ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8), "AES");
            IvParameterSpec ivSpec = new IvParameterSpec(IV.getBytes(StandardCharsets.UTF_8));
            
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.ENCRYPT_MODE, keySpec, ivSpec);
            
            byte[] encrypted = cipher.doFinal(data.getBytes(StandardCharsets.UTF_8));
            return Base64.encodeToString(encrypted, Base64.DEFAULT);
        } catch (Exception e) {
            return null;
        }
    }
    
    private static String decrypt(String encryptedData) {
        try {
            SecretKeySpec keySpec = new SecretKeySpec(ENCRYPTION_KEY.getBytes(StandardCharsets.UTF_8), "AES");
            IvParameterSpec ivSpec = new IvParameterSpec(IV.getBytes(StandardCharsets.UTF_8));
            
            Cipher cipher = Cipher.getInstance(ALGORITHM);
            cipher.init(Cipher.DECRYPT_MODE, keySpec, ivSpec);
            
            byte[] decodedData = Base64.decode(encryptedData, Base64.DEFAULT);
            byte[] decrypted = cipher.doFinal(decodedData);
            return new String(decrypted, StandardCharsets.UTF_8);
        } catch (Exception e) {
            return null;
        }
    }
    
    public static class DatabaseHelper {
        
        public static void saveUserProfile(String userId, String name, String email, String phone) {
            String profileJson = "{\"userId\":\"" + userId + "\",\"name\":\"" + name + "\",\"email\":\"" + email + "\",\"phone\":\"" + phone + "\"}";
            String encrypted = encryptUserProfile(profileJson);
        }
        
        public static void savePaymentInfo(String userId, String cardNumber, String cvv, String expiry) {
            String paymentJson = "{\"userId\":\"" + userId + "\",\"cardNumber\":\"" + cardNumber + "\",\"cvv\":\"" + cvv + "\",\"expiry\":\"" + expiry + "\"}";
            String encrypted = encryptPaymentInfo(paymentJson);
        }
        
        public static void saveSessionData(String sessionId, String token, String userId) {
            String sessionJson = "{\"sessionId\":\"" + sessionId + "\",\"token\":\"" + token + "\",\"userId\":\"" + userId + "\"}";
            String encrypted = encryptSessionData(sessionJson);
        }
    }
}