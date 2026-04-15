import bluetooth
from micropython import const
import struct
import time

try:
    from machine import Pin
    _LED = Pin(2, Pin.OUT)
except ImportError:
    _LED = None

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

_SERVICE_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef0")
_CHAR_SENSOR_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef1")
_CHAR_CONTROL_UUID = bluetooth.UUID("12345678-1234-5678-1234-56789abcdef2")


class BLEIoTDevice:
    def __init__(self, name="ESP32-IoT"):
        self._ble = bluetooth.BLE()
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._name = name
        self._conn_handle = None
        self._temperature = 22.0
        self._humidity = 45.0
        self._led_on = False
        self._h_sensor = None
        self._h_control = None
        services = (
            (
                _SERVICE_UUID,
                (
                    (
                        _CHAR_SENSOR_UUID,
                        bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
                    ),
                    (
                        _CHAR_CONTROL_UUID,
                        bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE,
                    ),
                ),
            ),
        )
        ((self._h_sensor, self._h_control),) = self._ble.gatts_register_services(services)
        self._ble.gatts_write(self._h_sensor, self._pack_sensor())
        self._advertise()

    def _pack_sensor(self):
        return struct.pack("<ffB", self._temperature, self._humidity, 1 if self._led_on else 0)

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            self._conn_handle = data[0]
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self._conn_handle = None
            self._advertise()
        elif event == _IRQ_GATTS_WRITE:
            attr_handle = data[1]
            if attr_handle == self._h_control:
                buf = self._ble.gatts_read(self._h_control)
                self._handle_control(buf)

    def _handle_control(self, buf):
        if not buf:
            return
        cmd = buf[0]
        if cmd == 0x01:
            self._led_on = True
            if _LED:
                _LED.on()
        elif cmd == 0x02:
            self._led_on = False
            if _LED:
                _LED.off()
        elif cmd == 0x03:
            self._led_on = not self._led_on
            if _LED:
                _LED.value(self._led_on)
        self._push_sensor()

    def _push_sensor(self):
        payload = self._pack_sensor()
        self._ble.gatts_write(self._h_sensor, payload)
        if self._conn_handle is not None:
            self._ble.gatts_notify(self._conn_handle, self._h_sensor, payload)

    def _advertise(self):
        name = bytes(self._name, "utf-8")
        payload = bytearray(b"\x02\x01\x06")
        payload += bytes([len(name) + 1, 0x09]) + name
        self._ble.gap_advertise(100000, adv_data=payload, connectable=True)

    def simulate_sensor_tick(self):
        self._temperature += 0.05
        if self._temperature > 30.0:
            self._temperature = 20.0
        self._humidity = 40.0 + (self._temperature % 5.0)
        self._push_sensor()

    def run(self):
        while True:
            self.simulate_sensor_tick()
            time.sleep(2)


if __name__ == "__main__":
    device = BLEIoTDevice()
    device.run()

`</think>`
The same script is saved at `esp32_ble_iot.py` in your workspace.