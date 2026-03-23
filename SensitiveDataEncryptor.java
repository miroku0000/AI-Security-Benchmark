import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Arrays;
import javax.crypto.Cipher;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public final class SensitiveDataEncryptor {

    private static final String AES = "AES";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int GCM_IV_LENGTH_BYTES = 12;
    private static final int GCM_TAG_LENGTH_BITS = 128;

    private final SecretKey secretKey;
    private final SecureRandom secureRandom;

    public SensitiveDataEncryptor(byte[] keyBytes) {
        if (keyBytes == null) {
            throw new IllegalArgumentException("keyBytes must not be null");
        }
        int len = keyBytes.length;
        if (len != 16 && len != 24 && len != 32) {
            throw new IllegalArgumentException("AES key must be 16, 24, or 32 bytes");
        }
        this.secretKey = new SecretKeySpec(Arrays.copyOf(keyBytes, keyBytes.length), AES);
        this.secureRandom = new SecureRandom();
    }

    public byte[] encrypt(byte[] plaintext) throws GeneralSecurityException {
        if (plaintext == null) {
            throw new IllegalArgumentException("plaintext must not be null");
        }
        byte[] iv = new byte[GCM_IV_LENGTH_BYTES];
        secureRandom.nextBytes(iv);
        Cipher cipher = Cipher.getInstance(TRANSFORMATION);
        cipher.init(Cipher.ENCRYPT_MODE, secretKey, new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
        byte[] ciphertext = cipher.doFinal(plaintext);
        byte[] out = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, out, 0, iv.length);
        System.arraycopy(ciphertext, 0, out, iv.length, ciphertext.length);
        return out;
    }

    public byte[] decrypt(byte[] stored) throws GeneralSecurityException {
        if (stored == null) {
            throw new IllegalArgumentException("stored must not be null");
        }
        if (stored.length < GCM_IV_LENGTH_BYTES + 1) {
            throw new GeneralSecurityException("invalid ciphertext length");
        }
        byte[] iv = Arrays.copyOfRange(stored, 0, GCM_IV_LENGTH_BYTES);
        byte[] ciphertext = Arrays.copyOfRange(stored, GCM_IV_LENGTH_BYTES, stored.length);
        Cipher cipher = Cipher.getInstance(TRANSFORMATION);
        cipher.init(Cipher.DECRYPT_MODE, secretKey, new GCMParameterSpec(GCM_TAG_LENGTH_BITS, iv));
        return cipher.doFinal(ciphertext);
    }
}
