#ifndef IOT_SENSOR_ENCRYPT_H
#define IOT_SENSOR_ENCRYPT_H

#include <stddef.h>
#include <stdint.h>

void iot_sensor_crypto_ctr_xor(const uint8_t key[16], const uint8_t nonce[8],
                               uint8_t *data, size_t len);

#endif
