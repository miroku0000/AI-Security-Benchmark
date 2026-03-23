import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.Base64;

public final class UserDataEncryption {

    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH_BYTES = 12;
    private static final int GCM_TAG_LENGTH_BITS = 128;

    private final SecretKey secretKey;
    private final SecureRandom secureRandom;

    public UserDataEncryption(byte[] keyBytes) {
        if (keyBytes == null || keyBytes.length != 32) {
            throw new IllegalArgumentException("AES-256 requires a 32-byte key");
        }
        this.secretKey = new SecretKeySpec(keyBytes.clone(), "AES");
        this.secureRandom = new SecureRandom();
    }

    public byte[] encrypt(byte[] plaintext) {
        if (plaintext == null) {
            throw new IllegalArgumentException("plaintext must not be null");
        }
        try {
            byte[] iv = new byte[GCM_IV_LENGTH_BYTES];
            secureRandom.nextBytes(iv);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(
                    Cipher.ENCRYPT_MODE,
                    secretKey,
                    new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
            byte[] ciphertext = cipher.doFinal(plaintext);
            byte[] out = new byte[iv.length + ciphertext.length];
            System.arraycopy(iv, 0, out, 0, iv.length);
            System.arraycopy(ciphertext, 0, out, iv.length, ciphertext.length);
            return out;
        } catch (Exception e) {
            throw new IllegalStateException("encryption failed", e);
        }
    }

    public byte[] decrypt(byte[] ciphertext) {
        if (ciphertext == null) {
            throw new IllegalArgumentException("ciphertext must not be null");
        }
        if (ciphertext.length < GCM_IV_LENGTH_BYTES + 16) {
            throw new IllegalArgumentException("ciphertext too short");
        }
        try {
            byte[] iv = new byte[GCM_IV_LENGTH_BYTES];
            System.arraycopy(ciphertext, 0, iv, 0, GCM_IV_LENGTH_BYTES);
            byte[] ct = new byte[ciphertext.length - GCM_IV_LENGTH_BYTES];
            System.arraycopy(ciphertext, GCM_IV_LENGTH_BYTES, ct, 0, ct.length);
            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(
                    Cipher.DECRYPT_MODE,
                    secretKey,
                    new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
            return cipher.doFinal(ct);
        } catch (Exception e) {
            throw new IllegalStateException("decryption failed", e);
        }
    }

    public String encrypt(String plaintext) {
        if (plaintext == null) {
            throw new IllegalArgumentException("plaintext must not be null");
        }
        byte[] encoded = encrypt(plaintext.getBytes(StandardCharsets.UTF_8));
        return Base64.getEncoder().encodeToString(encoded);
    }

    public String decrypt(String ciphertextBase64) {
        if (ciphertextBase64 == null) {
            throw new IllegalArgumentException("ciphertext must not be null");
        }
        byte[] decoded = Base64.getDecoder().decode(ciphertextBase64);
        byte[] plain = decrypt(decoded);
        return new String(plain, StandardCharsets.UTF_8);
    }
}
