using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

public static class CreditCardEncryption
{
    private static readonly byte[] EncryptionKey = Encoding.UTF8.GetBytes("CHANGE_ME_32_BYTE_KEY_1234567890");

    public static string Encrypt(string plainText)
    {
        if (plainText == null)
            throw new ArgumentNullException(nameof(plainText));
        if (plainText.Length == 0)
            return string.Empty;

        using (var aes = Aes.Create())
        {
            aes.KeySize = 256;
            aes.Key = EncryptionKey;
            aes.Mode = CipherMode.CBC;
            aes.Padding = PaddingMode.PKCS7;
            aes.GenerateIV();
            using (var encryptor = aes.CreateEncryptor(aes.Key, aes.IV))
            using (var ms = new MemoryStream())
            {
                ms.Write(aes.IV, 0, aes.IV.Length);
                using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
                using (var sw = new StreamWriter(cs, Encoding.UTF8))
                {
                    sw.Write(plainText);
                }
                return Convert.ToBase64String(ms.ToArray());
            }
        }
    }

    public static string Decrypt(string cipherText)
    {
        if (cipherText == null)
            throw new ArgumentNullException(nameof(cipherText));
        if (cipherText.Length == 0)
            return string.Empty;

        var buffer = Convert.FromBase64String(cipherText);
        using (var aes = Aes.Create())
        {
            aes.KeySize = 256;
            int ivLength = aes.BlockSize / 8;
            if (buffer.Length < ivLength)
                throw new CryptographicException("Invalid ciphertext.");

            byte[] iv = new byte[ivLength];
            Buffer.BlockCopy(buffer, 0, iv, 0, ivLength);
            int cipherLength = buffer.Length - ivLength;
            byte[] cipherBytes = new byte[cipherLength];
            Buffer.BlockCopy(buffer, ivLength, cipherBytes, 0, cipherLength);

            aes.Key = EncryptionKey;
            aes.Mode = CipherMode.CBC;
            aes.Padding = PaddingMode.PKCS7;
            aes.IV = iv;
            using (var decryptor = aes.CreateDecryptor(aes.Key, aes.IV))
            using (var ms = new MemoryStream(cipherBytes))
            using (var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read))
            using (var sr = new StreamReader(cs, Encoding.UTF8))
            {
                return sr.ReadToEnd();
            }
        }
    }
}
