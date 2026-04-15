import socket
import struct
import json
import machine
import time

# CoAP Constants
COAP_VERSION = 1
COAP_TYPE_CON = 0  # Confirmable
COAP_TYPE_ACK = 2  # Acknowledgement
COAP_METHOD_GET = 1
COAP_METHOD_PUT = 3
COAP_RESPONSE_CONTENT = (2, 5)      # 2.05 Content
COAP_RESPONSE_CHANGED = (2, 4)      # 2.04 Changed
COAP_RESPONSE_BAD_REQUEST = (4, 0)  # 4.00 Bad Request
COAP_RESPONSE_NOT_FOUND = (4, 4)    # 4.04 Not Found
COAP_RESPONSE_METHOD_NOT_ALLOWED = (4, 5)  # 4.05 Method Not Allowed
COAP_CONTENT_FORMAT_PLAIN = 0
COAP_CONTENT_FORMAT_JSON = 50
COAP_OPTION_URI_PATH = 11
COAP_OPTION_CONTENT_FORMAT = 12

# Device state
light_state = {"on": False, "brightness": 0}


def read_temperature():
    try:
        adc = machine.ADC(0)
        raw = adc.read_u16()
        voltage = raw * 3.3 / 65535
        temp_c = (voltage - 0.5) * 100.0
        return round(temp_c, 1)
    except Exception:
        return 22.5


def parse_coap(data):
    if len(data) < 4:
        return None
    byte0 = data[0]
    version = (byte0 >> 6) & 0x03
    msg_type = (byte0 >> 4) & 0x03
    token_len = byte0 & 0x0F
    code_byte = data[1]
    code_class = (code_byte >> 5) & 0x07
    code_detail = code_byte & 0x1F
    msg_id = struct.unpack("!H", data[2:4])[0]

    if version != COAP_VERSION or token_len > 8:
        return None

    offset = 4
    token = data[offset:offset + token_len]
    offset += token_len

    options = []
    prev_option = 0
    while offset < len(data):
        if data[offset] == 0xFF:
            offset += 1
            break
        delta = (data[offset] >> 4) & 0x0F
        length = data[offset] & 0x0F
        offset += 1
        if delta == 13:
            delta = data[offset] + 13
            offset += 1
        elif delta == 14:
            delta = struct.unpack("!H", data[offset:offset + 2])[0] + 269
            offset += 2
        if length == 13:
            length = data[offset] + 13
            offset += 1
        elif length == 14:
            length = struct.unpack("!H", data[offset:offset + 2])[0] + 269
            offset += 2
        option_number = prev_option + delta
        option_value = data[offset:offset + length]
        offset += length
        options.append((option_number, option_value))
        prev_option = option_number

    payload = data[offset:] if offset < len(data) else b""

    return {
        "version": version,
        "type": msg_type,
        "token_len": token_len,
        "code": (code_class, code_detail),
        "msg_id": msg_id,
        "token": token,
        "options": options,
        "payload": payload,
    }


def build_coap_response(msg_type, code, msg_id, token, payload=b"", content_format=None):
    token_len = len(token)
    byte0 = (COAP_VERSION << 6) | (msg_type << 4) | token_len
    code_byte = (code[0] << 5) | code[1]
    header = struct.pack("!BBH", byte0, code_byte, msg_id)
    resp = bytearray(header) + bytearray(token)

    if content_format is not None:
        if content_format < 256:
            resp += bytes([COAP_OPTION_CONTENT_FORMAT << 4 | 1, content_format])
        else:
            resp += bytes([COAP_OPTION_CONTENT_FORMAT << 4 | 2])
            resp += struct.pack("!H", content_format)

    if payload:
        resp += b"\xFF" + payload

    return bytes(resp)


def get_uri_path(options):
    parts = []
    for option_number, option_value in options:
        if option_number == COAP_OPTION_URI_PATH:
            parts.append(option_value.decode("utf-8"))
    return "/" + "/".join(parts)


def handle_request(parsed):
    global light_state
    code_class, code_detail = parsed["code"]
    method = code_detail if code_class == 0 else None
    uri = get_uri_path(parsed["options"])
    msg_type = COAP_TYPE_ACK if parsed["type"] == COAP_TYPE_CON else parsed["type"]

    if uri == "/sensors/temp":
        if method == COAP_METHOD_GET:
            temp = read_temperature()
            payload = json.dumps({"temperature": temp, "unit": "C"}).encode()
            return build_coap_response(msg_type, COAP_RESPONSE_CONTENT, parsed["msg_id"],
                                       parsed["token"], payload, COAP_CONTENT_FORMAT_JSON)
        return build_coap_response(msg_type, COAP_RESPONSE_METHOD_NOT_ALLOWED,
                                   parsed["msg_id"], parsed["token"])

    if uri == "/actuators/light":
        if method == COAP_METHOD_GET:
            payload = json.dumps(light_state).encode()
            return build_coap_response(msg_type, COAP_RESPONSE_CONTENT, parsed["msg_id"],
                                       parsed["token"], payload, COAP_CONTENT_FORMAT_JSON)
        if method == COAP_METHOD_PUT:
            try:
                body = json.loads(parsed["payload"].decode("utf-8"))
                if "on" in body:
                    light_state["on"] = bool(body["on"])
                if "brightness" in body:
                    val = int(body["brightness"])
                    if 0 <= val <= 100:
                        light_state["brightness"] = val
                payload = json.dumps(light_state).encode()
                return build_coap_response(msg_type, COAP_RESPONSE_CHANGED, parsed["msg_id"],
                                           parsed["token"], payload, COAP_CONTENT_FORMAT_JSON)
            except (ValueError, KeyError):
                return build_coap_response(msg_type, COAP_RESPONSE_BAD_REQUEST,
                                           parsed["msg_id"], parsed["token"])
        return build_coap_response(msg_type, COAP_RESPONSE_METHOD_NOT_ALLOWED,
                                   parsed["msg_id"], parsed["token"])

    return build_coap_response(msg_type, COAP_RESPONSE_NOT_FOUND,
                               parsed["msg_id"], parsed["token"])


def main():
    addr = socket.getaddrinfo("0.0.0.0", 5683)[0][-1]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(addr)
    print("CoAP server listening on port 5683")

    while True:
        try:
            data, client_addr = sock.recvfrom(256)
            parsed = parse_coap(data)
            if parsed is None:
                continue
            response = handle_request(parsed)
            sock.sendto(response, client_addr)
        except Exception as e:
            print("Error:", e)


if __name__ == "__main__":
    main()