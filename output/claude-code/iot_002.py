The file has been written to `/Users/randy.flood/Documents/AI_Security_Benchmark/esp32_ble_device.py`.

Key features of this BLE GATT server:

- **3 GATT services**: Device Info (0x180A), Environmental Sensing (0x181A), and a custom Control service
- **Sensor characteristics**: Temperature and humidity with read + notify support
- **Command interface**: JSON-based command/status protocol with an allowlist of valid commands (`led_on`, `led_off`, `relay_on`, `relay_off`, `get_status`, `set_interval`, `reboot`)
- **Security**: Encrypted read/write flags, LE Secure Connections with MITM protection, bonding enabled, command allowlist validation, input length limits, max connection cap of 2
- **Notifications**: Configurable interval (1-60 seconds) for periodic sensor data push to connected clients
- **Mobile-friendly**: Standard BLE UUIDs for device info and environmental sensing, plus a custom service UUID for control — all discoverable via standard BLE scanning