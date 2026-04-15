static void ascon_init(ascon_state_t *s, const uint8_t key[IOT_KEY_SIZE], const uint8_t nonce[IOT_NONCE_SIZE]) {
    const uint64_t iv = 0x80800c0800000000ULL;
    const uint64_t k0 = load64_be(key);
    const uint64_t k1 = load64_be(key + 8);
    const uint64_t n0 = load64_be(nonce);
    const uint64_t n1 = load64_be(nonce + 8);