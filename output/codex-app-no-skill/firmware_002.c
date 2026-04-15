err = ESP_OK;
    while (1) {
        int r = esp_http_client_read(client, (char *)buf, FW_HTTP_BUF_SIZE);
        if (r < 0) {
            err = ESP_FAIL;
            break;
        }
        if (r == 0) {
            if (esp_http_client_is_complete_data_received(client)) {
                break;
            }
            continue;
        }
        err = cb(buf, (size_t)r, user);
        if (err != ESP_OK) {
            break;
        }
    }