static bool cloud_connect(const char *endpoint, uint16_t port, const char *device_id, const char *api_secret_key) {
    if (endpoint == NULL || device_id == NULL || api_secret_key == NULL) return false;
    if (strlen(endpoint) == 0 || strlen(device_id) == 0 || strlen(api_secret_key) == 0) return false;