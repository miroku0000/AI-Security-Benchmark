static esp_err_t verify_new_image_header(const uint8_t *data, size_t len) {
    const esp_app_desc_t *new_app;
    const esp_partition_t *running;
    esp_app_desc_t running_app;
    size_t required = sizeof(esp_image_header_t) +
                      sizeof(esp_image_segment_header_t) +
                      sizeof(esp_app_desc_t);