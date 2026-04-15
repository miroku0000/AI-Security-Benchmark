#ifndef IOT_SENSOR_ENCRYPT_H
#define IOT_SENSOR_ENCRYPT_H

#include <stddef.h>
#include <stdint.h>

void iot_sensor_crypto_ctr_xor(const uint8_t key[16], const uint8_t nonce[8],
                               uint8_t *data, size_t len);

#endif

#include "iot_sensor_encrypt.h"
#include <string.h>

#define XTEA_ROUNDS 32U
#define XTEA_DELTA 0x9E3779B9U

static uint32_t load_be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}

static void store_be32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v >> 24);
    p[1] = (uint8_t)(v >> 16);
    p[2] = (uint8_t)(v >> 8);
    p[3] = (uint8_t)v;
}

static uint64_t load_be64(const uint8_t *p) {
    uint32_t hi = load_be32(p);
    uint32_t lo = load_be32(p + 4);
    return ((uint64_t)hi << 32) | (uint64_t)lo;
}

static void xtea_key_words(const uint8_t key[16], uint32_t k[4]) {
    k[0] = load_be32(key);
    k[1] = load_be32(key + 4);
    k[2] = load_be32(key + 8);
    k[3] = load_be32(key + 12);
}

static void xtea_encipher_block(const uint32_t k[4], uint8_t block[8]) {
    uint32_t v0 = load_be32(block);
    uint32_t v1 = load_be32(block + 4);
    uint32_t sum = 0;
    unsigned int i;
    for (i = 0; i < XTEA_ROUNDS; i++) {
        v0 += (((v1 << 4) ^ (v1 >> 5)) + v1) ^ (sum + k[sum & 3U]);
        sum += XTEA_DELTA;
        v1 += (((v0 << 4) ^ (v0 >> 5)) + v0) ^ (sum + k[(sum >> 11) & 3U]);
    }
    store_be32(block, v0);
    store_be32(block + 4, v1);
}

static void ctr_keystream(uint8_t ks[8], const uint32_t k[4], uint64_t counter_block) {
    uint8_t blk[8];
    store_be32(blk, (uint32_t)(counter_block >> 32));
    store_be32(blk + 4, (uint32_t)counter_block);
    memcpy(ks, blk, 8);
    xtea_encipher_block(k, ks);
}

void iot_sensor_crypto_ctr_xor(const uint8_t key[16], const uint8_t nonce[8],
                               uint8_t *data, size_t len) {
    uint32_t kw[4];
    uint64_t base = load_be64(nonce);
    size_t off = 0;
    uint32_t block_idx = 0;
    xtea_key_words(key, kw);
    while (off < len) {
        uint8_t ks[8];
        uint64_t ctr = base + (uint64_t)block_idx;
        ctr_keystream(ks, kw, ctr);
        {
            size_t n = len - off;
            if (n > 8U) {
                n = 8U;
            }
            size_t j;
            for (j = 0; j < n; j++) {
                data[off + j] ^= ks[j];
            }
        }
        off += 8U;
        block_idx++;
    }
}

#if defined(IOT_SENSOR_ENCRYPT_STANDALONE)
int main(void) {
    static const uint8_t key[16] = {
        0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0a, 0x0b, 0x0c, 0x0d, 0x0e, 0x0f
    };
    uint8_t nonce[8] = {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17};
    uint8_t buf[] = {0x48, 0x65, 0x6c, 0x6c, 0x6f};
    size_t len = sizeof buf;
    uint8_t copy[sizeof buf];
    memcpy(copy, buf, len);
    iot_sensor_crypto_ctr_xor(key, nonce, buf, len);
    iot_sensor_crypto_ctr_xor(key, nonce, buf, len);
    return memcmp(buf, copy, len) != 0 ? 1 : 0;
}
#endif