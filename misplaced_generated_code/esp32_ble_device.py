import bluetooth
import struct
import time
import machine
import json
from micropython import const

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)

_FLAG_READ = const(0x0002)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_READ_ENCRYPTED = const(0x0200)
_FLAG_WRITE_ENCRYPTED = const(0x1000)

_DEVICE_INFO_SERVICE_UUID = bluetooth.UUID(0x180A)
_MANUFACTURER_CHAR = (bluetooth.UUID(0x2A29), _FLAG_READ)
_MODEL_CHAR = (bluetooth.UUID(0x2A24), _FLAG_READ)
_FIRMWARE_CHAR = (bluetooth.UUID(0x2A26), _FLAG_READ)

_DEVICE_INFO_SERVICE = (_DEVICE_INFO_SERVICE_UUID, (_MANUFACTURER_CHAR, _MODEL_CHAR, _FIRMWARE_CHAR))

_ENV_SENSE_UUID = bluetooth.UUID(0x181A)
_TEMP_CHAR = (bluetooth.UUID(0x2A6E), _FLAG_READ | _FLAG_NOTIFY | _FLAG_READ_ENCRYPTED)
_HUMIDITY_CHAR = (bluetooth.UUID(0x2A6F), _FLAG_READ | _FLAG_NOTIFY | _FLAG_READ_ENCRYPTED)

_ENV_SENSE_SERVICE = (_ENV_SENSE_UUID, (_TEMP_CHAR, _HUMIDITY_CHAR))

_CONTROL_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
_COMMAND_CHAR = (
    bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1"),
    _FLAG_WRITE | _FLAG_WRITE_ENCRYPTED,
)
_STATUS_CHAR = (
    bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2"),
    _FLAG_READ | _FLAG_NOTIFY | _FLAG_READ_ENCRYPTED,
)

_CONTROL_SERVICE = (_CONTROL_SERVICE_UUID, (_COMMAND_CHAR, _STATUS_CHAR))

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)
_ADV_TYPE_APPEARANCE = const(0x19)

_MAX_CONNECTIONS = const(2)
_PAIRING_REQUIRED = True
_AUTH_TIMEOUT_MS = const(30000)

ALLOWED_COMMANDS = {
    "led_on", "led_off", "relay_on", "relay_off",
    "get_status", "set_interval", "reboot",
}

MAX_COMMAND_LEN = const(128)


def _encode_adv_data(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    if limited_disc or br_edr:
        flags = (0x01 if limited_disc else 0x02) | (0x00 if br_edr else 0x04)
        payload += struct.pack("BBB", 2, _ADV_TYPE_FLAGS, flags)

    if name:
        name_bytes = name.encode("utf-8")[:20]
        payload += struct.pack("BB", len(name_bytes) + 1, _ADV_TYPE_NAME) + name_bytes

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                payload += struct.pack("BBH", 3, _ADV_TYPE_UUID16_COMPLETE, struct.unpack("<H", b)[0])

    if appearance:
        payload += struct.pack("BBH", 3, _ADV_TYPE_APPEARANCE, appearance)

    return payload


class BLEDeviceServer:
    def __init__(self, name="ESP32-IoT-Device"):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.config(gap_name=name[:16])

        if _PAIRING_REQUIRED:
            self._ble.config(
                bond=True,
                mitm=True,
                le_secure=True,
                io=const(0x04),
            )

        self._ble.irq(self._irq)
        self._connections = set()
        self._authenticated = set()
        self._name = name

        self._led = machine.Pin(2, machine.Pin.OUT)
        self._relay = None
        try:
            self._relay = machine.Pin(4, machine.Pin.OUT)
        except Exception:
            pass

        self._temp_value = 2200
        self._humidity_value = 5000
        self._status = {"led": False, "relay": False, "interval": 5000, "uptime": 0}
        self._boot_ticks = time.ticks_ms()
        self._notify_interval = 5000
        self._last_notify = time.ticks_ms()

        handles = self._ble.gatts_register_services(
            [_DEVICE_INFO_SERVICE, _ENV_SENSE_SERVICE, _CONTROL_SERVICE]
        )

        self._h_manufacturer, self._h_model, self._h_firmware = handles[0]
        self._h_temp, self._h_humidity = handles[1]
        self._h_command, self._h_status = handles[2]

        self._ble.gatts_write(self._h_manufacturer, b"ESP32-IoT-Co")
        self._ble.gatts_write(self._h_model, b"IoT-Sensor-v1")
        self._ble.gatts_write(self._h_firmware, b"1.0.0")

        self._update_sensor_data()
        self._update_status()
        self._advertise()
        print("BLE Device Server started:", name)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, addr_type, addr = data
            if len(self._connections) >= _MAX_CONNECTIONS:
                self._ble.gap_disconnect(conn_handle)
                print("Connection rejected: max connections reached")
                return
            self._connections.add(conn_handle)
            print("Connected:", conn_handle)
            if len(self._connections) < _MAX_CONNECTIONS:
                self._advertise()

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, addr_type, addr = data
            self._connections.discard(conn_handle)
            self._authenticated.discard(conn_handle)
            print("Disconnected:", conn_handle)
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            value = self._ble.gatts_read(attr_handle)
            if attr_handle == self._h_command:
                self._handle_command(conn_handle, value)

        elif event == _IRQ_GATTS_READ_REQUEST:
            conn_handle, attr_handle = data
            if attr_handle == self._h_temp or attr_handle == self._h_humidity:
                self._update_sensor_data()

    def _handle_command(self, conn_handle, value):
        if not value or len(value) > MAX_COMMAND_LEN:
            self._write_status(conn_handle, {"error": "invalid_length"})
            return

        try:
            cmd_str = value.decode("utf-8").strip()
        except (UnicodeError, ValueError):
            self._write_status(conn_handle, {"error": "invalid_encoding"})
            return

        try:
            cmd_data = json.loads(cmd_str)
        except ValueError:
            cmd_data = {"cmd": cmd_str}

        if not isinstance(cmd_data, dict):
            self._write_status(conn_handle, {"error": "invalid_format"})
            return

        command = cmd_data.get("cmd", "")

        if command not in ALLOWED_COMMANDS:
            self._write_status(conn_handle, {"error": "unknown_command", "cmd": command})
            return

        result = self._execute_command(command, cmd_data)
        self._write_status(conn_handle, result)

    def _execute_command(self, command, cmd_data):
        if command == "led_on":
            self._led.value(1)
            self._status["led"] = True
            return {"ok": True, "led": "on"}

        elif command == "led_off":
            self._led.value(0)
            self._status["led"] = False
            return {"ok": True, "led": "off"}

        elif command == "relay_on":
            if self._relay:
                self._relay.value(1)
                self._status["relay"] = True
                return {"ok": True, "relay": "on"}
            return {"error": "relay_not_available"}

        elif command == "relay_off":
            if self._relay:
                self._relay.value(0)
                self._status["relay"] = False
                return {"ok": True, "relay": "off"}
            return {"error": "relay_not_available"}

        elif command == "get_status":
            self._status["uptime"] = time.ticks_diff(time.ticks_ms(), self._boot_ticks) // 1000
            return {"ok": True, "status": self._status}

        elif command == "set_interval":
            interval = cmd_data.get("value", 5000)
            if isinstance(interval, int) and 1000 <= interval <= 60000:
                self._notify_interval = interval
                self._status["interval"] = interval
                return {"ok": True, "interval": interval}
            return {"error": "invalid_interval", "range": "1000-60000"}

        elif command == "reboot":
            self._write_status(None, {"ok": True, "action": "rebooting"})
            time.sleep_ms(500)
            machine.reset()

        return {"error": "unhandled"}

    def _write_status(self, conn_handle, data):
        status_bytes = json.dumps(data).encode("utf-8")
        self._ble.gatts_write(self._h_status, status_bytes)
        if conn_handle is not None and conn_handle in self._connections:
            self._ble.gatts_notify(conn_handle, self._h_status, status_bytes)

    def _update_sensor_data(self):
        try:
            adc = machine.ADC(machine.Pin(36))
            adc.atten(machine.ADC.ATTN_11DB)
            raw = adc.read()
            self._temp_value = int((raw / 4095.0) * 5000)
        except Exception:
            self._temp_value += (time.ticks_ms() % 5) - 2

        self._humidity_value = max(0, min(10000, self._humidity_value + (time.ticks_ms() % 7) - 3))

        self._ble.gatts_write(self._h_temp, struct.pack("<h", self._temp_value))
        self._ble.gatts_write(self._h_humidity, struct.pack("<H", self._humidity_value))

    def _update_status(self):
        self._status["uptime"] = time.ticks_diff(time.ticks_ms(), self._boot_ticks) // 1000
        status_bytes = json.dumps(self._status).encode("utf-8")
        self._ble.gatts_write(self._h_status, status_bytes)

    def _advertise(self):
        adv_data = _encode_adv_data(
            name=self._name,
            services=[_ENV_SENSE_UUID, bluetooth.UUID(0x180A)],
            appearance=0x0540,
        )
        self._ble.gap_advertise(250000, adv_payload=adv_data, connectable=True)

    def notify_loop(self):
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_notify) >= self._notify_interval:
                self._last_notify = now
                self._update_sensor_data()
                self._update_status()

                temp_data = struct.pack("<h", self._temp_value)
                humidity_data = struct.pack("<H", self._humidity_value)

                for conn in list(self._connections):
                    try:
                        self._ble.gatts_notify(conn, self._h_temp, temp_data)
                        self._ble.gatts_notify(conn, self._h_humidity, humidity_data)
                    except OSError:
                        self._connections.discard(conn)
                        self._authenticated.discard(conn)

            time.sleep_ms(100)


def main():
    server = BLEDeviceServer(name="ESP32-IoT-Dev")
    server.notify_loop()


if __name__ == "__main__":
    main()
