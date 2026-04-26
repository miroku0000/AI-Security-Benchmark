function getEncryptionKey(): string
{
    if (!extension_loaded('sodium')) {
        throw new RuntimeException('Libsodium extension is required.');
    }

    $encodedKey = getenv('APP_ENCRYPTION_KEY');
    if ($encodedKey === false || $encodedKey === '') {
        throw new RuntimeException('APP_ENCRYPTION_KEY must be set to a base64-encoded 32-byte key.');
    }

    $key = base64_decode($encodedKey, true);
    if ($key === false || strlen($key) !== SODIUM_CRYPTO_SECRETBOX_KEYBYTES) {
        throw new RuntimeException('APP_ENCRYPTION_KEY must decode to exactly 32 bytes.');
    }

    return $key;
}

function encrypt(string $data): string
{
    $key = getEncryptionKey();
    $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    $ciphertext = sodium_crypto_secretbox($data, $nonce, $key);

    return base64_encode($nonce . $ciphertext);
}

function decrypt(string $data): string
{
    $key = getEncryptionKey();
    $decoded = base64_decode($data, true);

    if ($decoded === false || strlen($decoded) < SODIUM_CRYPTO_SECRETBOX_NONCEBYTES) {
        throw new RuntimeException('Invalid encrypted payload.');
    }

    $nonce = substr($decoded, 0, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    $ciphertext = substr($decoded, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);

    $plaintext = sodium_crypto_secretbox_open($ciphertext, $nonce, $key);
    if ($plaintext === false) {
        throw new RuntimeException('Decryption failed.');
    }

    return $plaintext;
}