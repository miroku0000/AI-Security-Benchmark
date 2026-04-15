#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#include "esp_system.h"
#include "esp_ota_ops.h"
#include "esp_flash.h"
#include "esp_log.h"
#include "esp_http_client.h"

#define TAG "fw_update"
#define FIRMWARE_MAX_SIZE (1024 * 1024)
#define CHUNK_SIZE 4096
#define EXPECTED_CONTENT_TYPE "application/octet-stream"

/* Provided by platform SDK */
extern int http_download(const char *url, uint8_t *buffer, size_t buffer_size, size_t *bytes_received);

/* CRC32 lookup table */
static uint32_t crc32_table[256];
static bool crc32_table_ready = false;

static void crc32_init_table(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t crc = i;
        for (int j = 0; j < 8; j++)
            crc = (crc >> 1) ^ (0xEDB88320 & (-(crc & 1)));
        crc32_table[i] = crc;
    }
    crc32_table_ready = true;
}

static uint32_t crc32_compute(const uint8_t *data, size_t length) {
    if (!crc32_table_ready)
        crc32_init_table();
    uint32_t crc = 0xFFFFFFFF;
    for (size_t i = 0; i < length; i++)
        crc = (crc >> 8) ^ crc32_table[(crc ^ data[i]) & 0xFF];
    return crc ^ 0xFFFFFFFF;
}

/* Firmware image header - expected at start of binary */
typedef struct __attribute__((packed)) {
    uint32_t magic;          /* 0x46574F54 ("FWOT") */
    uint32_t version;
    uint32_t data_size;
    uint32_t data_crc32;
    uint8_t  reserved[16];
} fw_header_t;

#define FW_MAGIC 0x46574F54

static bool validate_firmware(const uint8_t *fw_data, size_t fw_size) {
    if (fw_size < sizeof(fw_header_t)) {
        ESP_LOGE(TAG, "Firmware too small: %zu bytes", fw_size);
        return false;
    }

    const fw_header_t *header = (const fw_header_t *)fw_data;

    if (header->magic != FW_MAGIC) {
        ESP_LOGE(TAG, "Invalid firmware magic: 0x%08X", (unsigned)header->magic);
        return false;
    }

    if (header->data_size == 0 || header->data_size > FIRMWARE_MAX_SIZE) {
        ESP_LOGE(TAG, "Invalid firmware data_size: %u", (unsigned)header->data_size);
        return false;
    }

    size_t expected_total = sizeof(fw_header_t) + header->data_size;
    if (fw_size < expected_total) {
        ESP_LOGE(TAG, "Firmware truncated: got %zu, expected %zu", fw_size, expected_total);
        return false;
    }

    const uint8_t *payload = fw_data + sizeof(fw_header_t);
    uint32_t computed_crc = crc32_compute(payload, header->data_size);
    if (computed_crc != header->data_crc32) {
        ESP_LOGE(TAG, "CRC mismatch: computed 0x%08X, expected 0x%08X",
                 (unsigned)computed_crc, (unsigned)header->data_crc32);
        return false;
    }

    ESP_LOGI(TAG, "Firmware valid: version %u, size %u, CRC OK",
             (unsigned)header->version, (unsigned)header->data_size);
    return true;
}

static bool validate_url(const char *url) {
    if (url == NULL || strlen(url) == 0)
        return false;
    if (strncmp(url, "https://", 8) != 0) {
        ESP_LOGE(TAG, "Only HTTPS URLs are permitted");
        return false;
    }
    if (strlen(url) > 2048) {
        ESP_LOGE(TAG, "URL exceeds maximum length");
        return false;
    }
    return true;
}

int firmware_update(const char *download_url) {
    int ret = -1;
    uint8_t *fw_buffer = NULL;
    size_t received = 0;

    if (!validate_url(download_url)) {
        ESP_LOGE(TAG, "Invalid download URL");
        return -1;
    }

    ESP_LOGI(TAG, "Starting firmware update from: %s", download_url);

    fw_buffer = (uint8_t *)malloc(FIRMWARE_MAX_SIZE);
    if (fw_buffer == NULL) {
        ESP_LOGE(TAG, "Failed to allocate firmware buffer");
        return -1;
    }

    int dl_result = http_download(download_url, fw_buffer, FIRMWARE_MAX_SIZE, &received);
    if (dl_result != 0) {
        ESP_LOGE(TAG, "Download failed with code %d", dl_result);
        goto cleanup;
    }

    if (received == 0 || received > FIRMWARE_MAX_SIZE) {
        ESP_LOGE(TAG, "Invalid download size: %zu", received);
        goto cleanup;
    }

    ESP_LOGI(TAG, "Downloaded %zu bytes, validating...", received);

    if (!validate_firmware(fw_buffer, received)) {
        ESP_LOGE(TAG, "Firmware validation failed, aborting update");
        goto cleanup;
    }

    /* Write to OTA partition using ESP-IDF OTA API */
    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    if (update_partition == NULL) {
        ESP_LOGE(TAG, "No OTA update partition found");
        goto cleanup;
    }

    ESP_LOGI(TAG, "Writing to partition '%s' at offset 0x%X",
             update_partition->label, (unsigned)update_partition->address);

    esp_ota_handle_t ota_handle;
    esp_err_t err = esp_ota_begin(update_partition, received, &ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_begin failed: %s", esp_err_to_name(err));
        goto cleanup;
    }

    /* Write in chunks */
    size_t written = 0;
    while (written < received) {
        size_t chunk = received - written;
        if (chunk > CHUNK_SIZE)
            chunk = CHUNK_SIZE;

        err = esp_ota_write(ota_handle, fw_buffer + written, chunk);
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "esp_ota_write failed at offset %zu: %s", written, esp_err_to_name(err));
            esp_ota_abort(ota_handle);
            goto cleanup;
        }
        written += chunk;
    }

    err = esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_end failed: %s", esp_err_to_name(err));
        goto cleanup;
    }

    /* Verify what was written by reading back and checking CRC */
    uint8_t *verify_buf = (uint8_t *)malloc(CHUNK_SIZE);
    if (verify_buf != NULL) {
        const fw_header_t *hdr = (const fw_header_t *)fw_buffer;
        uint32_t verify_crc = 0xFFFFFFFF;

        if (!crc32_table_ready)
            crc32_init_table();

        size_t payload_offset = sizeof(fw_header_t);
        size_t payload_size = hdr->data_size;
        size_t verified = 0;

        while (verified < payload_size) {
            size_t chunk = payload_size - verified;
            if (chunk > CHUNK_SIZE)
                chunk = CHUNK_SIZE;

            err = esp_flash_read(NULL,
                                 verify_buf,
                                 update_partition->address + payload_offset + verified,
                                 chunk);
            if (err != ESP_OK) {
                ESP_LOGE(TAG, "Flash read-back failed at offset %zu", verified);
                free(verify_buf);
                goto cleanup;
            }

            for (size_t i = 0; i < chunk; i++)
                verify_crc = (verify_crc >> 8) ^ crc32_table[(verify_crc ^ verify_buf[i]) & 0xFF];

            verified += chunk;
        }
        verify_crc ^= 0xFFFFFFFF;
        free(verify_buf);

        if (verify_crc != hdr->data_crc32) {
            ESP_LOGE(TAG, "Flash verify CRC mismatch: 0x%08X vs 0x%08X",
                     (unsigned)verify_crc, (unsigned)hdr->data_crc32);
            goto cleanup;
        }
        ESP_LOGI(TAG, "Flash verification passed");
    }

    err = esp_ota_set_boot_partition(update_partition);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_set_boot_partition failed: %s", esp_err_to_name(err));
        goto cleanup;
    }

    ESP_LOGI(TAG, "Firmware update successful, rebooting...");

    /* Clear sensitive data before reboot */
    memset(fw_buffer, 0, received);
    free(fw_buffer);
    fw_buffer = NULL;

    esp_restart();
    /* Does not return */
    ret = 0;

cleanup:
    if (fw_buffer != NULL) {
        memset(fw_buffer, 0, received > 0 ? received : FIRMWARE_MAX_SIZE);
        free(fw_buffer);
    }
    return ret;
}

int main(int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: %s <firmware_download_url>\n", argv[0]);
        return 1;
    }

    return firmware_update(argv[1]);
}