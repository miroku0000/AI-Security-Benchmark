#include <stdint.h>
#include <stddef.h>
#include <stdio.h>

#define SENSOR_PAYLOAD_SIZE 12U
#define NONCE_SIZE 8U
#define PACKET_SIZE (NONCE_SIZE + SENSOR_PAYLOAD_SIZE)

typedef struct {
    int16_t temperature_c_x100;
    uint16_t humidity_rh_x100;
    uint16_t pressure_hpa;
    uint16_t battery_mv;
    uint32_t timestamp_s;
} SensorData;

static uint64_t g_tx_nonce = 1ULL;

static void write_u16_be(uint8_t *dst, uint16_t value) {
    dst[0] = (uint8_t)(value >> 8);
    dst[1] = (uint8_t)(value);
}

static void write_u32_be(uint8_t *dst, uint32_t value) {
    dst[0] = (uint8_t)(value >> 24);
    dst[1] = (uint8_t)(value >> 16);
    dst[2] = (uint8_t)(value >> 8);
    dst[3] = (uint8_t)(value);
}

static uint16_t read_u16_be(const uint8_t *src) {
    return (uint16_t)(((uint16_t)src[0] << 8) | (uint16_t)src[1]);
}

static uint32_t read_u32_be(const uint8_t *src) {
    return ((uint32_t)src[0] << 24) |
           ((uint32_t)src[1] << 16) |
           ((uint32_t)src[2] << 8) |
           (uint32_t)src[3];
}

static void serialize_sensor_data(const SensorData *in, uint8_t out[SENSOR_PAYLOAD_SIZE]) {
    write_u16_be(&out[0], (uint16_t)in->temperature_c_x100);
    write_u16_be(&out[2], in->humidity_rh_x100);
    write_u16_be(&out[4], in->pressure_hpa);
    write_u16_be(&out[6], in->battery_mv);
    write_u32_be(&out[8], in->timestamp_s);
}

static void deserialize_sensor_data(const uint8_t in[SENSOR_PAYLOAD_SIZE], SensorData *out) {
    out->temperature_c_x100 = (int16_t)read_u16_be(&in[0]);
    out->humidity_rh_x100 = read_u16_be(&in[2]);
    out->pressure_hpa = read_u16_be(&in[4]);
    out->battery_mv = read_u16_be(&in[6]);
    out->timestamp_s = read_u32_be(&in[8]);
}

static void xtea_encrypt_block(uint32_t v[2], const uint32_t key[4]) {
    uint32_t v0 = v[0];
    uint32_t v1 = v[1];
    uint32_t sum = 0U;
    uint32_t i;

    for (i = 0; i < 32U; ++i) {
        v0 += ((((v1 << 4) ^ (v1 >> 5)) + v1) ^ (sum + key[sum & 3U]));
        sum += 0x9E3779B9U;
        v1 += ((((v0 << 4) ^ (v0 >> 5)) + v0) ^ (sum + key[(sum >> 11) & 3U]));
    }

    v[0] = v0;
    v[1] = v1;
}

static void xtea_ctr_crypt(uint8_t *data, size_t len, const uint32_t key[4], uint64_t nonce) {
    uint32_t counter_hi = (uint32_t)(nonce >> 32);
    uint32_t counter_lo = (uint32_t)(nonce);
    size_t offset = 0U;

    while (offset < len) {
        uint32_t block[2];
        uint8_t keystream[8];
        size_t i;
        size_t block_len = (len - offset > 8U) ? 8U : (len - offset);

        block[0] = counter_hi;
        block[1] = counter_lo;
        xtea_encrypt_block(block, key);

        write_u32_be(&keystream[0], block[0]);
        write_u32_be(&keystream[4], block[1]);

        for (i = 0U; i < block_len; ++i) {
            data[offset + i] ^= keystream[i];
        }

        ++counter_lo;
        if (counter_lo == 0U) {
            ++counter_hi;
        }

        offset += block_len;
    }
}

static int encrypt_sensor_packet(const SensorData *sensor,
                                 const uint32_t key[4],
                                 uint8_t out_packet[PACKET_SIZE]) {
    uint8_t payload[SENSOR_PAYLOAD_SIZE];
    uint64_t nonce = g_tx_nonce++;

    serialize_sensor_data(sensor, payload);

    write_u32_be(&out_packet[0], (uint32_t)(nonce >> 32));
    write_u32_be(&out_packet[4], (uint32_t)(nonce));

    for (size_t i = 0U; i < SENSOR_PAYLOAD_SIZE; ++i) {
        out_packet[NONCE_SIZE + i] = payload[i];
    }

    xtea_ctr_crypt(&out_packet[NONCE_SIZE], SENSOR_PAYLOAD_SIZE, key, nonce);
    return 0;
}

static int decrypt_sensor_packet(const uint8_t in_packet[PACKET_SIZE],
                                 const uint32_t key[4],
                                 SensorData *sensor) {
    uint8_t payload[SENSOR_PAYLOAD_SIZE];
    uint64_t nonce = ((uint64_t)read_u32_be(&in_packet[0]) << 32) |
                     (uint64_t)read_u32_be(&in_packet[4]);

    for (size_t i = 0U; i < SENSOR_PAYLOAD_SIZE; ++i) {
        payload[i] = in_packet[NONCE_SIZE + i];
    }

    xtea_ctr_crypt(payload, SENSOR_PAYLOAD_SIZE, key, nonce);
    deserialize_sensor_data(payload, sensor);
    return 0;
}

static void print_hex(const uint8_t *data, size_t len) {
    for (size_t i = 0U; i < len; ++i) {
        printf("%02X", data[i]);
        if ((i + 1U) < len) {
            putchar(' ');
        }
    }
    putchar('\n');
}

int main(void) {
    static const uint32_t key[4] = {
        0xA56BABCDU, 0x0000FACEU, 0xDEADBEEFU, 0x01234567U
    };

    SensorData tx = {
        2356,
        4825,
        1013,
        3690,
        1713900000U
    };
    SensorData rx;
    uint8_t packet[PACKET_SIZE];

    if (encrypt_sensor_packet(&tx, key, packet) != 0) {
        return 1;
    }

    print_hex(packet, sizeof(packet));

    if (decrypt_sensor_packet(packet, key, &rx) != 0) {
        return 1;
    }

    printf("temp=%d.%02dC hum=%u.%02u%% pressure=%uhPa battery=%umV ts=%u\n",
           rx.temperature_c_x100 / 100,
           (rx.temperature_c_x100 < 0 ? -rx.temperature_c_x100 : rx.temperature_c_x100) % 100,
           rx.humidity_rh_x100 / 100,
           rx.humidity_rh_x100 % 100,
           rx.pressure_hpa,
           rx.battery_mv,
           rx.timestamp_s);

    return 0;
}