import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.Base64;

public final class SensitiveDataEncryptor {
    private static final String ALGORITHM = "AES";
    private static final String TRANSFORMATION = "AES/GCM/NoPadding";
    private static final int KEY_SIZE_BITS = 256;
    private static final int IV_LENGTH_BYTES = 12;
    private static final int TAG_LENGTH_BITS = 128;

    private final SecretKey secretKey;
    private final SecureRandom secureRandom = new SecureRandom();

    public SensitiveDataEncryptor(byte[] rawKey) {
        if (rawKey == null || (rawKey.length != 16 && rawKey.length != 24 && rawKey.length != 32)) {
            throw new IllegalArgumentException("AES key must be 16, 24, or 32 bytes long.");
        }
        this.secretKey = new SecretKeySpec(rawKey, ALGORITHM);
    }

    public SensitiveDataEncryptor(String base64Key) {
        this(decodeBase64Key(base64Key));
    }

    public String encrypt(String plainText) {
        if (plainText == null) {
            throw new IllegalArgumentException("Plain text cannot be null.");
        }

        try {
            byte[] iv = new byte[IV_LENGTH_BYTES];
            secureRandom.nextBytes(iv);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.ENCRYPT_MODE, secretKey, new GCMParameterSpec(TAG_LENGTH_BITS, iv));

            byte[] cipherText = cipher.doFinal(plainText.getBytes(StandardCharsets.UTF_8));
            byte[] payload = ByteBuffer.allocate(iv.length + cipherText.length)
                    .put(iv)
                    .put(cipherText)
                    .array();

            return Base64.getEncoder().encodeToString(payload);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Encryption failed.", e);
        }
    }

    public String decrypt(String encryptedValue) {
        if (encryptedValue == null) {
            throw new IllegalArgumentException("Encrypted value cannot be null.");
        }

        try {
            byte[] payload = Base64.getDecoder().decode(encryptedValue);
            if (payload.length <= IV_LENGTH_BYTES) {
                throw new IllegalArgumentException("Encrypted value is invalid.");
            }

            ByteBuffer buffer = ByteBuffer.wrap(payload);
            byte[] iv = new byte[IV_LENGTH_BYTES];
            buffer.get(iv);

            byte[] cipherText = new byte[buffer.remaining()];
            buffer.get(cipherText);

            Cipher cipher = Cipher.getInstance(TRANSFORMATION);
            cipher.init(Cipher.DECRYPT_MODE, secretKey, new GCMParameterSpec(TAG_LENGTH_BITS, iv));

            byte[] plainText = cipher.doFinal(cipherText);
            return new String(plainText, StandardCharsets.UTF_8);
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Decryption failed.", e);
        }
    }

    public static String generateBase64Key() {
        try {
            KeyGenerator keyGenerator = KeyGenerator.getInstance(ALGORITHM);
            keyGenerator.init(KEY_SIZE_BITS);
            return Base64.getEncoder().encodeToString(keyGenerator.generateKey().getEncoded());
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("Key generation failed.", e);
        }
    }

    private static byte[] decodeBase64Key(String base64Key) {
        if (base64Key == null || base64Key.isBlank()) {
            throw new IllegalArgumentException("Base64 key cannot be null or blank.");
        }
        return Base64.getDecoder().decode(base64Key);
    }

    public static void main(String[] args) {
        if (args.length == 1 && "--generate-key".equals(args[0])) {
            System.out.println(generateBase64Key());
            return;
        }

        if (args.length != 3) {
            throw new IllegalArgumentException(
                    "Usage: java SensitiveDataEncryptor <encrypt|decrypt> <base64Key> <value> or java SensitiveDataEncryptor --generate-key"
            );
        }

        SensitiveDataEncryptor encryptor = new SensitiveDataEncryptor(args[1]);
        String result;

        switch (args[0].toLowerCase()) {
            case "encrypt":
                result = encryptor.encrypt(args[2]);
                break;
            case "decrypt":
                result = encryptor.decrypt(args[2]);
                break;
            default:
                throw new IllegalArgumentException("First argument must be 'encrypt' or 'decrypt'.");
        }

        System.out.println(result);
    }
}