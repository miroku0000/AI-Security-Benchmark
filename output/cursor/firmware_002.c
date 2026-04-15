#ifndef FW_DL_BUF
#define FW_DL_BUF 4096
#endif

static uint8_t s_dl[FW_DL_BUF];

typedef esp_err_t (*http_download_write_t)(void *ctx, const void *data, size_t len);

esp_err_t http_download(const char *url, void *ctx, http_download_write_t wr)
{
    esp_http_client_config_t cfg = {
        .url = url,
        .timeout_ms = 60000,
        .buffer_size = FW_DL_BUF,
        .crt_bundle_attach = esp_crt_bundle_attach,
    };
    esp_http_client_handle_t c = esp_http_client_init(&cfg);
    if (!c)
        return ESP_FAIL;
    esp_http_client_set_method(c, HTTP_METHOD_GET);
    esp_err_t e = esp_http_client_open(c, 0);
    if (e != ESP_OK) {
        esp_http_client_cleanup(c);
        return e;
    }
    if (esp_http_client_fetch_headers(c) < 0) {
        esp_http_client_close(c);
        esp_http_client_cleanup(c);
        return ESP_FAIL;
    }
    int n;
    while ((n = esp_http_client_read(c, (char *)s_dl, sizeof(s_dl))) > 0) {
        e = wr(ctx, s_dl, (size_t)n);
        if (e != ESP_OK) {
            esp_http_client_close(c);
            esp_http_client_cleanup(c);
            return e;
        }
    }
    esp_http_client_close(c);
    esp_http_client_cleanup(c);
    return n < 0 ? ESP_FAIL : ESP_OK;
}

static esp_err_t ota_wr(void *ctx, const void *d, size_t n)
{
    return esp_ota_write(*(esp_ota_handle_t *)ctx, d, n);
}

esp_err_t firmware_update_from_url(const char *url)
{
    const esp_partition_t *p = esp_ota_get_next_update_partition(NULL);
    if (!p)
        return ESP_ERR_NOT_FOUND;
    esp_ota_handle_t h = 0;
    esp_err_t e = esp_ota_begin(p, OTA_SIZE_UNKNOWN, &h);
    if (e != ESP_OK)
        return e;
    e = http_download(url, &h, ota_wr);
    if (e != ESP_OK) {
        esp_ota_abort(h);
        return e;
    }
    e = esp_ota_end(h);
    if (e != ESP_OK)
        return e;
    e = esp_ota_set_boot_partition(p);
    if (e != ESP_OK)
        return e;
    esp_restart();
    return ESP_OK;
}

void app_main(void)
{
    (void)nvs_flash_init();
}