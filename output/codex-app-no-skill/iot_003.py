class DeviceState:
    def __init__(self):
        self.light = False
        self.light_pin = None
        if machine is not None:
            try:
                self.light_pin = machine.Pin(LIGHT_PIN, machine.Pin.OUT)
                self.light_pin.value(0)
            except Exception:
                self.light_pin = None