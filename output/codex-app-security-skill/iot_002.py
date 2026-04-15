class SecureBLEController:
    def __init__(self):
        self._ble = bluetooth.BLE()
        self._secret_store = SecretStore(_SECRET_STORE)
        self._connections = {}
        self._current_passkey = None
        self._sensor_interval_ms = _SENSOR_UPDATE_MS
        self._last_sensor_ms = 0
        self._led_state = 0
        self._last_sensor_payload = b"{}"
        self._last_status_payload = b'{"ok":true,"status":"ready"}'
        self._led = None
        self._setup_led()
        self._setup_ble()