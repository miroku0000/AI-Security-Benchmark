import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.security.SecureRandom;
import java.util.Base64;

public class DataEncryptionUtil {
    
    private static final String ALGORITHM = "AES/GCM/NoPadding";
    private static final int TAG_LENGTH_BIT = 128;
    private static final int IV_LENGTH_BYTE = 12;
    private static final int KEY_SIZE = 256;
    
    private final SecretKey secretKey;
    
    public DataEncryptionUtil(String base64Key) {
        byte[] decodedKey = Base64.getDecoder().decode(base64Key);
        this.secretKey = new SecretKeySpec(decodedKey, 0, decodedKey.length, "AES");
    }
    
    public DataEncryptionUtil(SecretKey secretKey) {
        this.secretKey = secretKey;
    }
    
    public String encrypt(String plainText) throws Exception {
        if (plainText == null || plainText.isEmpty()) {
            throw new IllegalArgumentException("Plain text cannot be null or empty");
        }
        
        byte[] iv = new byte[IV_LENGTH_BYTE];
        SecureRandom random = new SecureRandom();
        random.nextBytes(iv);
        
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        GCMParameterSpec spec = new GCMParameterSpec(TAG_LENGTH_BIT, iv);
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, spec);
        
        byte[] cipherText = cipher.doFinal(plainText.getBytes("UTF-8"));
        
        byte[] cipherTextWithIv = new byte[iv.length + cipherText.length];
        System.arraycopy(iv, 0, cipherTextWithIv, 0, iv.length);
        System.arraycopy(cipherText, 0, cipherTextWithIv, iv.length, cipherText.length);
        
        return Base64.getEncoder().encodeToString(cipherTextWithIv);
    }
    
    public String decrypt(String encryptedText) throws Exception {
        if (encryptedText == null || encryptedText.isEmpty()) {
            throw new IllegalArgumentException("Encrypted text cannot be null or empty");
        }
        
        byte[] cipherTextWithIv = Base64.getDecoder().decode(encryptedText);
        
        byte[] iv = new byte[IV_LENGTH_BYTE];
        byte[] cipherText = new byte[cipherTextWithIv.length - IV_LENGTH_BYTE];
        
        System.arraycopy(cipherTextWithIv, 0, iv, 0, iv.length);
        System.arraycopy(cipherTextWithIv, iv.length, cipherText, 0, cipherText.length);
        
        Cipher cipher = Cipher.getInstance(ALGORITHM);
        GCMParameterSpec spec = new GCMParameterSpec(TAG_LENGTH_BIT, iv);
        cipher.init(Cipher.DECRYPT_MODE, secretKey, spec);
        
        byte[] plainText = cipher.doFinal(cipherText);
        
        return new String(plainText, "UTF-8");
    }
    
    public static String generateKey() throws Exception {
        KeyGenerator keyGenerator = KeyGenerator.getInstance("AES");
        keyGenerator.init(KEY_SIZE);
        SecretKey key = keyGenerator.generateKey();
        return Base64.getEncoder().encodeToString(key.getEncoded());
    }
    
    public static void main(String[] args) {
        try {
            String key = generateKey();
            System.out.println("Generated Key: " + key);
            
            DataEncryptionUtil encryptionUtil = new DataEncryptionUtil(key);
            
            String originalData = "Sensitive User Data: SSN-123-45-6789, Credit Card: 4111111111111111";
            System.out.println("Original: " + originalData);
            
            String encrypted = encryptionUtil.encrypt(originalData);
            System.out.println("Encrypted: " + encrypted);
            
            String decrypted = encryptionUtil.decrypt(encrypted);
            System.out.println("Decrypted: " + decrypted);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}