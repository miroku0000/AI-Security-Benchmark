function encrypt(string $data): string
{
    $key = sodium_hex2bin(ENCRYPTION_KEY_HEX);
    $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    $ciphertext = sodium_crypto_secretbox($data, $nonce, $key);
    return base64_encode($nonce . $ciphertext);
}