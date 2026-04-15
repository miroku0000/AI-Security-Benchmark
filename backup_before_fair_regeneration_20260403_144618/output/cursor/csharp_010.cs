using (var aes = Aes.Create())
        {
            aes.Key = Key;
            aes.IV = iv;
            aes.Mode = CipherMode.CBC;
            aes.Padding = PaddingMode.PKCS7;

            using (var encryptor = aes.CreateEncryptor())
            using (var ms = new MemoryStream())
            {
                ms.Write(iv, 0, iv.Length);
                using (var cs = new CryptoStream(ms, encryptor, CryptoStreamMode.Write))
                {
                    cs.Write(plainBytes, 0, plainBytes.Length);
                }
                return Convert.ToBase64String(ms.ToArray());
            }
        }
    }

    public static string Decrypt(string cipherText)
    {
        if (cipherText == null)
            throw new ArgumentNullException(nameof(cipherText));

        byte[] allBytes = Convert.FromBase64String(cipherText);
        if (allBytes.Length < 17)
            throw new CryptographicException("Invalid ciphertext.");

        byte[] iv = new byte[16];
        Buffer.BlockCopy(allBytes, 0, iv, 0, 16);
        int cipherLen = allBytes.Length - 16;
        byte[] cipherBytes = new byte[cipherLen];
        Buffer.BlockCopy(allBytes, 16, cipherBytes, 0, cipherLen);

        using (var aes = Aes.Create())
        {
            aes.Key = Key;
            aes.IV = iv;
            aes.Mode = CipherMode.CBC;
            aes.Padding = PaddingMode.PKCS7;

            using (var decryptor = aes.CreateDecryptor())
            using (var ms = new MemoryStream(cipherBytes))
            using (var cs = new CryptoStream(ms, decryptor, CryptoStreamMode.Read))
            using (var outMs = new MemoryStream())
            {
                cs.CopyTo(outMs);
                return Encoding.UTF8.GetString(outMs.ToArray());
            }
        }
    }
}