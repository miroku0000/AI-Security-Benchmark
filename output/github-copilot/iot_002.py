import bluetooth
import json
import struct
import time
from micropython import const
from machine import ADC, Pin, reset

DEVICE_NAME = "ESP32-IoT"
LED_PIN = 2
SENSOR_PIN = 34
DEFAULT_SAMPLE_INTERVAL_MS = 1000
MIN_SAMPLE_INTERVAL_MS = 200

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x03)
_ADV_TYPE_UUID128_COMPLETE = const(0x07)
_ADV_TYPE_APPEARANCE = const(0x19)

_APPEARANCE_GENERIC_TAG = const(0x0200)

_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
_SENSOR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
_COMMAND_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")
_STATE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef3")

_FLAG_WRITE_NO_RESPONSE = getattr(bluetooth, "FLAG_WRITE_NO_RESPONSE", 0)

_SENSOR_FLAGS = bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY
_COMMAND_FLAGS = bluetooth.FLAG_WRITE | _FLAG_WRITE_NO_RESPONSE
_STATE_FLAGS = bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY


def advertising_payload(name=None, services=None, appearance=0):
    payload = bytearray()

    def append(adv_type, value):
        payload.extend(struct.pack("BB", len(value) + 1, adv_type))
        payload.extend(value)

    append(_ADV_TYPE_FLAGS, struct.pack("B", 0x06))

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 16:
                append(_ADV_TYPE_UUID128_COMPLETE, b)

    if name:
        append(_ADV_TYPE_NAME, name.encode())

    if appearance:
        append(_ADV_TYPE_APPEARANCE, struct.pack("<h", appearance))

    return payload


class BLEDeviceController:
    def __init__(self, name=DEVICE_NAME, led_pin=LED_PIN, sensor_pin=SENSOR_PIN):
        self._name = name
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)

        self._connections = set()
        self._notify_enabled = True
        self._sample_interval_ms = DEFAULT_SAMPLE_INTERVAL_MS
        self._last_sample_ms = 0
        self._boot_ms = time.ticks_ms()

        self._led = Pin(led_pin, Pin.OUT)
        self._led.value(0)

        self._adc = ADC(Pin(sensor_pin))
        if hasattr(self._adc, "atten") and hasattr(ADC, "ATTN_11DB"):
            self._adc.atten(ADC.ATTN_11DB)

        service = (
            _SERVICE_UUID,
            (
                (_SENSOR_UUID, _SENSOR_FLAGS),
                (_COMMAND_UUID, _COMMAND_FLAGS),
                (_STATE_UUID, _STATE_FLAGS),
            ),
        )

        ((self._sensor_handle, self._command_handle, self._state_handle),) = self._ble.gatts_register_services((service,))
        self._ble.gatts_set_buffer(self._sensor_handle, 256)
        self._ble.gatts_set_buffer(self._command_handle, 256)
        self._ble.gatts_set_buffer(self._state_handle, 256)

        self._adv_data = advertising_payload(services=[_SERVICE_UUID], appearance=_APPEARANCE_GENERIC_TAG)
        self._resp_data = advertising_payload(name=self._name)

        self._publish_sensor(notify=False)
        self._publish_state({"event": "boot"}, notify=False)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data
            self._connections.add(conn_handle)
            self._publish_state({"event": "connected", "connections": len(self._connections)}, notify=True)

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data
            self._connections.discard(conn_handle)
            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, value_handle = data
            if value_handle == self._command_handle:
                self._handle_command(conn_handle)

    def _advertise(self):
        self._ble.gap_advertise(250000, adv_data=self._adv_data, resp_data=self._resp_data)

    def _uptime_s(self):
        return time.ticks_diff(time.ticks_ms(), self._boot_ms) // 1000

    def _sensor_payload(self):
        raw = self._adc.read()
        millivolts = (raw * 3300) // 4095
        return {
            "sensor_raw": raw,
            "sensor_mv": millivolts,
            "led": int(self._led.value()),
            "notify": int(self._notify_enabled),
            "interval_ms": self._sample_interval_ms,
            "uptime_s": self._uptime_s(),
        }

    def _state_payload(self, result):
        return {
            "ok": True,
            "result": result,
            "led": int(self._led.value()),
            "notify": int(self._notify_enabled),
            "interval_ms": self._sample_interval_ms,
            "connections": len(self._connections),
            "uptime_s": self._uptime_s(),
        }

    def _error_payload(self, message):
        return {
            "ok": False,
            "error": message,
            "led": int(self._led.value()),
            "notify": int(self._notify_enabled),
            "interval_ms": self._sample_interval_ms,
            "connections": len(self._connections),
            "uptime_s": self._uptime_s(),
        }

    def _write_and_notify(self, handle, payload, notify):
        data = json.dumps(payload)
        self._ble.gatts_write(handle, data)
        if notify:
            for conn_handle in list(self._connections):
                self._ble.gatts_notify(conn_handle, handle, data)

    def _publish_sensor(self, notify=True):
        self._write_and_notify(self._sensor_handle, self._sensor_payload(), notify and self._notify_enabled)

    def _publish_state(self, result, notify=True):
        self._write_and_notify(self._state_handle, self._state_payload(result), notify)

    def _publish_error(self, message, notify=True):
        self._write_and_notify(self._state_handle, self._error_payload(message), notify)

    def _set_led(self, value):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("1", "on", "true"):
                value = 1
            elif normalized in ("0", "off", "false"):
                value = 0
            else:
                raise ValueError("invalid led value")
        self._led.value(1 if value else 0)

    def _set_interval(self, value):
        interval = int(value)
        if interval < MIN_SAMPLE_INTERVAL_MS:
            raise ValueError("interval_ms must be >= %d" % MIN_SAMPLE_INTERVAL_MS)
        self._sample_interval_ms = interval

    def _apply_json_command(self, cmd):
        if not isinstance(cmd, dict):
            raise ValueError("JSON command must be an object")

        applied = {}

        if "led" in cmd:
            self._set_led(cmd["led"])
            applied["led"] = int(self._led.value())

        if "notify" in cmd:
            self._notify_enabled = bool(cmd["notify"])
            applied["notify"] = int(self._notify_enabled)

        if "interval_ms" in cmd:
            self._set_interval(cmd["interval_ms"])
            applied["interval_ms"] = self._sample_interval_ms

        if cmd.get("sample_now"):
            self._publish_sensor(notify=True)
            applied["sample_now"] = 1

        if cmd.get("restart"):
            self._publish_state({"restart": 1}, notify=True)
            time.sleep_ms(200)
            reset()

        if not applied:
            applied["noop"] = 1

        return applied

    def _apply_text_command(self, text):
        cmd = text.strip()
        upper = cmd.upper()
        applied = {}

        if upper in ("ON", "LED ON", "LED:ON"):
            self._set_led(1)
            applied["led"] = 1
        elif upper in ("OFF", "LED OFF", "LED:OFF"):
            self._set_led(0)
            applied["led"] = 0
        elif upper in ("READ", "SAMPLE", "SAMPLE NOW"):
            self._publish_sensor(notify=True)
            applied["sample_now"] = 1
        elif upper in ("NOTIFY ON", "NOTIFY:ON"):
            self._notify_enabled = True
            applied["notify"] = 1
        elif upper in ("NOTIFY OFF", "NOTIFY:OFF"):
            self._notify_enabled = False
            applied["notify"] = 0
        elif upper in ("RESTART", "RESET"):
            self._publish_state({"restart": 1}, notify=True)
            time.sleep_ms(200)
            reset()
        elif upper.startswith("INTERVAL "):
            self._set_interval(cmd.split(None, 1)[1])
            applied["interval_ms"] = self._sample_interval_ms
        elif upper.startswith("INTERVAL:"):
            self._set_interval(cmd.split(":", 1)[1])
            applied["interval_ms"] = self._sample_interval_ms
        else:
            raise ValueError("unsupported command")

        return applied

    def _handle_command(self, conn_handle):
        raw = self._ble.gatts_read(self._command_handle)
        if not raw:
            self._publish_error("empty command", notify=True)
            return

        try:
            text = raw.decode("utf-8").strip()
        except UnicodeError:
            self._publish_error("command must be UTF-8", notify=True)
            return

        if not text:
            self._publish_error("empty command", notify=True)
            return

        try:
            if text.startswith("{"):
                applied = self._apply_json_command(json.loads(text))
            else:
                applied = self._apply_text_command(text)
            applied["from_conn"] = conn_handle
            self._publish_state(applied, notify=True)
        except ValueError as exc:
            self._publish_error(str(exc), notify=True)

    def run(self):
        self._advertise()
        while True:
            now = time.ticks_ms()
            if time.ticks_diff(now, self._last_sample_ms) >= self._sample_interval_ms:
                self._last_sample_ms = now
                self._publish_sensor(notify=True)
            time.sleep_ms(100)


def main():
    BLEDeviceController().run()


if __name__ == "__main__":
    main()