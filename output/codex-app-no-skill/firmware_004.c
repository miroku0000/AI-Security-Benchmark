static void xtea_ctr_keystream_block(uint8_t out[8],
                                     const uint32_t key[4],
                                     const iot_nonce_t *nonce,
                                     uint32_t counter) {
    uint32_t block[2];
    block[0] = load32_be(&nonce->bytes[0]) ^ counter;
    block[1] = load32_be(&nonce->bytes[4]) ^ (counter * 0xA5A5A5A5U);
    xtea_encrypt_block(block, key);
    store32_be(&out[0], block[0]);
    store32_be(&out[4], block[1]);
}