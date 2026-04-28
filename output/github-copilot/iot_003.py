def _sleep_ms(ms):
    try:
        time.sleep_ms(ms)
    except AttributeError:
        time.sleep(ms / 1000.0)


def _resolve(path, default=None):
    obj = microcoapy
    for part in path.split("."):
        if not hasattr(obj, part):
            return default
        obj = getattr(obj, part)
    return obj


COAP_GET = _resolve("COAP_METHOD.COAP_GET", _resolve("COAP_GET", 1))
COAP_PUT = _resolve("COAP_METHOD.COAP_PUT", _resolve("COAP_PUT", 3))
COAP_CONTENT = _resolve("COAP_RESPONSE_CODE.COAP_CONTENT", _resolve("COAP_CONTENT", 69))
COAP_CHANGED = _resolve("COAP_RESPONSE_CODE.COAP_CHANGED", _resolve("COAP_CHANGED", 68))
COAP_BAD_REQUEST = _resolve("COAP_RESPONSE_CODE.COAP_BAD_REQUEST", _resolve("COAP_BAD_REQUEST", 128))
COAP_NOT_FOUND = _resolve("COAP_RESPONSE_CODE.COAP_NOT_FOUND", _resolve("COAP_NOT_FOUND", 132))
COAP_METHOD_NOT_ALLOWED = _resolve(
    "COAP_RESPONSE_CODE.COAP_METHOD_NOT_ALLOWED",
    _resolve("COAP_METHOD_NOT_ALLOWED", 133),
)
COAP_TYPE_ACK = _resolve("COAP_TYPE_ACK", 2)


def connect_wifi(ssid, password, timeout_s=15):
    if not ssid or network is None:
        return None

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        return wlan

    wlan.connect(ssid, password)
    start = time.time()
    while not wlan.isconnected():
        if time.time() - start >= timeout_s:
            raise RuntimeError("Wi-Fi connection timed out")
        _sleep_ms(250)
    return wlan


class DeviceState:
    def __init__(self):
        self.temp_c = FALLBACK_TEMP_C
        self.light = 0
        self.light_pin = self._init_light_pin()

    def _init_light_pin(self):
        if machine is None or not hasattr(machine, "Pin"):
            return None

        for pin_id in (LIGHT_PIN, 2):
            try:
                pin = machine.Pin(pin_id, machine.Pin.OUT)
                pin.value(0)
                return pin
            except Exception:
                pass
        return None

    def read_temp_c(self):
        if esp32 is not None and hasattr(esp32, "raw_temperature"):
            try:
                return round((esp32.raw_temperature() - 32.0) * 5.0 / 9.0, 2)
            except Exception:
                pass

        if machine is not None and hasattr(machine, "ADC"):
            for adc_id in (4, 0):
                try:
                    adc = machine.ADC(adc_id)
                    if hasattr(adc, "read_u16"):
                        raw = adc.read_u16()
                        voltage = raw * (3.3 / 65535.0)
                        temp_c = 27.0 - (voltage - 0.706) / 0.001721
                        return round(temp_c, 2)
                    if hasattr(adc, "read"):
                        raw = adc.read()
                        return round((raw / 1023.0) * 100.0, 2)
                except Exception:
                    pass

        return self.temp_c

    def set_light(self, value):
        if isinstance(value, bytes):
            value = value.decode().strip().lower()
        else:
            value = str(value).strip().lower()

        if value in ("1", "on", "true"):
            self.light = 1
        elif value in ("0", "off", "false"):
            self.light = 0
        else:
            return False

        if self.light_pin is not None:
            try:
                self.light_pin.value(self.light)
            except Exception:
                pass
        return True

    def light_payload(self):
        return b"on" if self.light else b"off"

    def temp_payload(self):
        return ("%.2f" % self.read_temp_c()).encode()


state = DeviceState()


def _request_method(packet):
    for name in ("method", "code", "request_code"):
        if hasattr(packet, name):
            return getattr(packet, name)
    return None


def _request_payload(packet):
    payload = getattr(packet, "payload", b"")
    if payload is None:
        return b""
    if isinstance(payload, bytes):
        return payload
    return str(payload).encode()


def _request_path(packet):
    for name in ("uri_path", "path", "url"):
        value = getattr(packet, name, None)
        if value:
            if isinstance(value, (list, tuple)):
                return "/" + "/".join([str(part).strip("/") for part in value if part])
            value = str(value)
            return value if value.startswith("/") else "/" + value

    parts = []
    options = getattr(packet, "options", None)
    if options:
        try:
            for opt in options:
                number = getattr(opt, "number", None)
                value = getattr(opt, "value", None)
                if number == 11:
                    if isinstance(value, bytes):
                        parts.append(value.decode())
                    else:
                        parts.append(str(value))
        except Exception:
            parts = []

    return "/" + "/".join(parts) if parts else "/"


def _message_id(packet):
    for name in ("messageid", "message_id", "msg_id"):
        if hasattr(packet, name):
            return getattr(packet, name)
    return 0


def _token(packet):
    return getattr(packet, "token", b"")


def _sender(packet, args):
    if len(args) >= 3:
        return args[1], args[2]
    if len(args) == 2:
        sender = args[1]
        if isinstance(sender, tuple) and len(sender) >= 2:
            return sender[0], sender[1]

    ip = getattr(packet, "sourceIp", None)
    port = getattr(packet, "sourcePort", None)
    if ip is not None and port is not None:
        return ip, port

    return None, None


def _send_response(server, packet, ip, port, code, payload=b"", content_format=0):
    if payload is None:
        payload = b""
    elif isinstance(payload, str):
        payload = payload.encode()
    elif not isinstance(payload, bytes):
        payload = str(payload).encode()

    if hasattr(packet, "respond"):
        try:
            packet.respond(payload, code)
            return
        except Exception:
            pass

    message_id = _message_id(packet)
    token = _token(packet)

    send_response = getattr(server, "sendResponse", None)
    if send_response is not None:
        for args in (
            (ip, port, message_id, payload, code, token, content_format, COAP_TYPE_ACK),
            (ip, port, message_id, payload, code, token, content_format),
            ((ip, port), message_id, payload, code, token, content_format),
            ((ip, port), message_id, payload, code),
        ):
            try:
                send_response(*args)
                return
            except Exception:
                pass

    send_packet = getattr(server, "sendPacket", None)
    packet_cls = getattr(microcoapy, "CoapPacket", None)
    if send_packet is not None and packet_cls is not None and ip is not None and port is not None:
        try:
            response = packet_cls()
            response.type = COAP_TYPE_ACK
            response.code = code
            response.messageid = message_id
            response.token = token
            response.payload = payload
            try:
                response.content_format = content_format
            except Exception:
                pass
            send_packet(response, ip, port)
            return
        except Exception:
            pass

    raise RuntimeError("Unable to send CoAP response with this microcoapy build")


def _handle_temp(server, packet, ip, port, method):
    if method == COAP_GET:
        _send_response(server, packet, ip, port, COAP_CONTENT, state.temp_payload())
    else:
        _send_response(server, packet, ip, port, COAP_METHOD_NOT_ALLOWED, b"read-only")


def _handle_light(server, packet, ip, port, method):
    if method == COAP_GET:
        _send_response(server, packet, ip, port, COAP_CONTENT, state.light_payload())
        return

    if method == COAP_PUT:
        if state.set_light(_request_payload(packet)):
            _send_response(server, packet, ip, port, COAP_CHANGED, state.light_payload())
        else:
            _send_response(server, packet, ip, port, COAP_BAD_REQUEST, b"invalid payload")
        return

    _send_response(server, packet, ip, port, COAP_METHOD_NOT_ALLOWED, b"method not allowed")


def on_request(*args):
    if not args:
        return

    packet = args[0]
    ip, port = _sender(packet, args)
    path = _request_path(packet)
    method = _request_method(packet)

    if path == "/sensors/temp":
        _handle_temp(coap_server, packet, ip, port, method)
    elif path == "/actuators/light":
        _handle_light(coap_server, packet, ip, port, method)
    else:
        _send_response(coap_server, packet, ip, port, COAP_NOT_FOUND, b"not found")


def _new_server():
    for cls_name in ("Coap", "CoAP", "CoapServer", "CoAPServer"):
        cls = getattr(microcoapy, cls_name, None)
        if cls is not None:
            return cls()
    raise RuntimeError("No compatible microcoapy server class found")


def _start_server(server, port):
    try:
        server.port = port
    except Exception:
        pass

    if hasattr(server, "addIncomingRequestCallback"):
        server.addIncomingRequestCallback(on_request)
    elif hasattr(server, "requestCallback"):
        server.requestCallback = on_request
    else:
        raise RuntimeError("This microcoapy build does not expose a request callback API")

    for start_args in ((), (port,), ("0.0.0.0", port)):
        try:
            server.start(*start_args)
            return
        except Exception:
            pass

    if hasattr(server, "listen"):
        for listen_args in ((), (port,), ("0.0.0.0", port)):
            try:
                server.listen(*listen_args)
                return
            except Exception:
                pass

    raise RuntimeError("Unable to start CoAP server")


def _server_loop(server):
    loop_fn = getattr(server, "loop", None)
    if loop_fn is not None:
        try:
            loop_fn(False)
            return
        except TypeError:
            loop_fn()
            return

    poll_fn = getattr(server, "poll", None)
    if poll_fn is not None:
        try:
            poll_fn(0)
        except TypeError:
            poll_fn()
        return

    raise RuntimeError("This microcoapy build does not expose loop/poll")


connect_wifi(WIFI_SSID, WIFI_PASSWORD)
coap_server = _new_server()
_start_server(coap_server, COAP_PORT)

while True:
    _server_loop(coap_server)
    _sleep_ms(POLL_DELAY_MS)