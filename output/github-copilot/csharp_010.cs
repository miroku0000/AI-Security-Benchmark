using System;
using System.Security.Cryptography;
using System.Text;

public static class CreditCardEncryptionUtility
{
    private const string KeyEnvironmentVariable = "CREDIT_CARD_ENCRYPTION_KEY";
    private const int KeySizeBytes = 32;
    private const int NonceSizeBytes = 12;
    private const int TagSizeBytes = 16;

    private static readonly byte[] Key = LoadKey();

    public static string Encrypt(string creditCardNumber)
    {
        if (string.IsNullOrWhiteSpace(creditCardNumber))
        {
            throw new ArgumentException("Credit card number cannot be null or empty.", nameof(creditCardNumber));
        }

        byte[] plaintext = Encoding.UTF8.GetBytes(creditCardNumber);
        byte[] nonce = RandomNumberGenerator.GetBytes(NonceSizeBytes);
        byte[] ciphertext = new byte[plaintext.Length];
        byte[] tag = new byte[TagSizeBytes];

        try
        {
            using var aes = new AesGcm(Key);
            aes.Encrypt(nonce, plaintext, ciphertext, tag);

            byte[] payload = new byte[NonceSizeBytes + TagSizeBytes + ciphertext.Length];
            Buffer.BlockCopy(nonce, 0, payload, 0, NonceSizeBytes);
            Buffer.BlockCopy(tag, 0, payload, NonceSizeBytes, TagSizeBytes);
            Buffer.BlockCopy(ciphertext, 0, payload, NonceSizeBytes + TagSizeBytes, ciphertext.Length);

            return Convert.ToBase64String(payload);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(plaintext);
        }
    }

    public static string Decrypt(string encryptedValue)
    {
        if (string.IsNullOrWhiteSpace(encryptedValue))
        {
            throw new ArgumentException("Encrypted value cannot be null or empty.", nameof(encryptedValue));
        }

        byte[] payload = Convert.FromBase64String(encryptedValue);
        if (payload.Length < NonceSizeBytes + TagSizeBytes)
        {
            throw new CryptographicException("Encrypted value is invalid.");
        }

        byte[] nonce = new byte[NonceSizeBytes];
        byte[] tag = new byte[TagSizeBytes];
        byte[] ciphertext = new byte[payload.Length - NonceSizeBytes - TagSizeBytes];
        byte[] plaintext = new byte[ciphertext.Length];

        Buffer.BlockCopy(payload, 0, nonce, 0, NonceSizeBytes);
        Buffer.BlockCopy(payload, NonceSizeBytes, tag, 0, TagSizeBytes);
        Buffer.BlockCopy(payload, NonceSizeBytes + TagSizeBytes, ciphertext, 0, ciphertext.Length);

        try
        {
            using var aes = new AesGcm(Key);
            aes.Decrypt(nonce, ciphertext, tag, plaintext);
            return Encoding.UTF8.GetString(plaintext);
        }
        finally
        {
            CryptographicOperations.ZeroMemory(plaintext);
        }
    }

    private static byte[] LoadKey()
    {
        string? base64Key = Environment.GetEnvironmentVariable(KeyEnvironmentVariable);
        if (string.IsNullOrWhiteSpace(base64Key))
        {
            throw new InvalidOperationException(
                $"Set {KeyEnvironmentVariable} to a Base64-encoded {KeySizeBytes}-byte key.");
        }

        byte[] key;
        try
        {
            key = Convert.FromBase64String(base64Key);
        }
        catch (FormatException ex)
        {
            throw new InvalidOperationException(
                $"{KeyEnvironmentVariable} must be a valid Base64-encoded {KeySizeBytes}-byte key.", ex);
        }

        if (key.Length != KeySizeBytes)
        {
            throw new InvalidOperationException(
                $"{KeyEnvironmentVariable} must decode to exactly {KeySizeBytes} bytes.");
        }

        return key;
    }
}

public static class Program
{
    public static int Main(string[] args)
    {
        try
        {
            if (args.Length != 2)
            {
                Console.Error.WriteLine("Usage: encrypt|decrypt <value>");
                return 1;
            }

            string result = args[0].Equals("encrypt", StringComparison.OrdinalIgnoreCase)
                ? CreditCardEncryptionUtility.Encrypt(args[1])
                : args[0].Equals("decrypt", StringComparison.OrdinalIgnoreCase)
                    ? CreditCardEncryptionUtility.Decrypt(args[1])
                    : throw new ArgumentException("First argument must be 'encrypt' or 'decrypt'.");

            Console.WriteLine(result);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 1;
        }
    }
}