import time
from microcoapy import coapy

_temp = 20.0
_light = 0


def _path(p):
    if isinstance(p, bytes):
        s = p.decode("utf-8").split("\x00", 1)[0].strip()
    else:
        s = str(p).strip()
    if s and not s.startswith("/"):
        s = "/" + s
    return s.rstrip("/") or "/"


def request_handler(request):
    global _temp, _light
    path = _path(request.path)
    m = request.method
    pl = request.payload if request.payload is not None else b""
    if path == "/sensors/temp":
        if m == coapy.COAP_METHOD_GET:
            return coapy.CoapResponse(
                coapy.COAP_RESPONSE_CODE_CONTENT, str(_temp).encode("utf-8")
            )
        if m == coapy.COAP_METHOD_PUT:
            try:
                _temp = float(pl.decode("utf-8").strip())
                return coapy.CoapResponse(coapy.COAP_RESPONSE_CODE_CHANGED, b"")
            except ValueError:
                return coapy.CoapResponse(0x80, b"")
    if path == "/actuators/light":
        if m == coapy.COAP_METHOD_GET:
            return coapy.CoapResponse(
                coapy.COAP_RESPONSE_CODE_CONTENT, str(_light).encode("utf-8")
            )
        if m == coapy.COAP_METHOD_PUT:
            try:
                _light = int(pl.decode("utf-8").strip())
                return coapy.CoapResponse(coapy.COAP_RESPONSE_CODE_CHANGED, b"")
            except ValueError:
                return coapy.CoapResponse(0x80, b"")
    return coapy.CoapResponse(coapy.COAP_RESPONSE_CODE_NOT_FOUND, b"")


coapy.addIncomingRequestCallback(request_handler)
coapy.start(5683)
while True:
    coapy.poll()
    time.sleep_ms(1)
