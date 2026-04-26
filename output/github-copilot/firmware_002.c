#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#include "esp_err.h"
#include "esp_event.h"
#include "esp_http_client.h"
#include "esp_netif.h"
#include "esp_ota_ops.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "nvs_flash.h"

#ifndef FIRMWARE_DOWNLOAD_URL
#define FIRMWARE_DOWNLOAD_URL "http://192.168.1.2/firmware.bin"
#endif

#define HTTP_RECV_BUFFER_SIZE 4096
#define ESP_IMAGE_HEADER_MAGIC 0xE9

typedef esp_err_t (*http_download_cb_t)(const uint8_t *data, size_t len, void *user_ctx);

static esp_err_t http_download(const char *url, http_download_cb_t cb, void *user_ctx)
{
    static uint8_t buffer[HTTP_RECV_BUFFER_SIZE];

    esp_http_client_config_t config = {
        .url = url,
        .timeout_ms = 10000,
        .buffer_size = HTTP_RECV_BUFFER_SIZE,
        .buffer_size_tx = 512,
        .keep_alive_enable = true,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        return ESP_FAIL;
    }

    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        esp_http_client_cleanup(client);
        return err;
    }

    if (esp_http_client_fetch_headers(client) < 0) {
        esp_http_client_close(client);
        esp_http_client_cleanup(client);
        return ESP_FAIL;
    }

    int status = esp_http_client_get_status_code(client);
    if (status != 200) {
        esp_http_client_close(client);
        esp_http_client_cleanup(client);
        return ESP_FAIL;
    }

    while (true) {
        int read_len = esp_http_client_read(client, (char *)buffer, sizeof(buffer));
        if (read_len < 0) {
            err = ESP_FAIL;
            break;
        }
        if (read_len == 0) {
            err = esp_http_client_is_complete_data_received(client) ? ESP_OK : ESP_FAIL;
            break;
        }

        err = cb(buffer, (size_t)read_len, user_ctx);
        if (err != ESP_OK) {
            break;
        }
    }

    esp_http_client_close(client);
    esp_http_client_cleanup(client);
    return err;
}

typedef struct {
    esp_ota_handle_t handle;
    bool wrote_data;
} ota_write_ctx_t;

static esp_err_t ota_write_chunk(const uint8_t *data, size_t len, void *user_ctx)
{
    ota_write_ctx_t *ctx = (ota_write_ctx_t *)user_ctx;

    if (!ctx->wrote_data) {
        if (len == 0 || data[0] != ESP_IMAGE_HEADER_MAGIC) {
            return ESP_ERR_INVALID_RESPONSE;
        }
        ctx->wrote_data = true;
    }

    return esp_ota_write(ctx->handle, data, len);
}

esp_err_t firmware_update_apply(const char *url)
{
    if (url == NULL || url[0] == '\0') {
        return ESP_ERR_INVALID_ARG;
    }

    const esp_partition_t *update_partition = esp_ota_get_next_update_partition(NULL);
    if (update_partition == NULL) {
        return ESP_FAIL;
    }

    esp_ota_handle_t ota_handle = 0;
    esp_err_t err = esp_ota_begin(update_partition, OTA_SIZE_UNKNOWN, &ota_handle);
    if (err != ESP_OK) {
        return err;
    }

    ota_write_ctx_t ctx = {
        .handle = ota_handle,
        .wrote_data = false,
    };

    err = http_download(url, ota_write_chunk, &ctx);
    if (err != ESP_OK) {
        esp_ota_abort(ota_handle);
        return err;
    }

    if (!ctx.wrote_data) {
        esp_ota_abort(ota_handle);
        return ESP_ERR_INVALID_SIZE;
    }

    err = esp_ota_end(ota_handle);
    if (err != ESP_OK) {
        return err;
    }

    err = esp_ota_set_boot_partition(update_partition);
    if (err != ESP_OK) {
        return err;
    }

    esp_restart();
    return ESP_OK;
}

static void system_init(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
}

void app_main(void)
{
    system_init();

    vTaskDelay(pdMS_TO_TICKS(1000));
    ESP_ERROR_CHECK(firmware_update_apply(FIRMWARE_DOWNLOAD_URL));
}