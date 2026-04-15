import binascii
import hashlib
import json
import network
import socket
import struct
import time

SSID = "YOUR_SSID"
PASSWORD = "YOUR_PASSWORD"
PORT = 8765

_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        deadline = time.ticks_ms() + 30000
        while not wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                raise OSError("WiFi connection timeout")
            time.sleep_ms(200)
    return wlan.ifconfig()[0]


def _ws_accept_key(key):
    digest = hashlib.sha1(key.encode() + _GUID).digest()
    return binascii.b2a_base64(digest).decode().strip()


def _recv_http_headers(sock):
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(512)
        if not chunk:
            return None, b""
        buf += chunk
        if len(buf) > 16384:
            return None, b""
    idx = buf.index(b"\r\n\r\n")
    header_bytes = buf[:idx]
    leftover = buf[idx + 4 :]
    lines = header_bytes.split(b"\r\n")
    headers = {}
    for line in lines[1:]:
        if b":" in line:
            k, v = line.split(b":", 1)
            headers[k.decode().strip().lower()] = v.decode().strip()
    return headers, leftover


def _send_handshake(sock, key):
    accept = _ws_accept_key(key)
    resp = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n"
        "\r\n"
    )
    sock.send(resp.encode())


def _send_ws_frame(sock, opcode, payload=b"", fin=True):
    b0 = (0x80 if fin else 0x00) | (opcode & 0x0F)
    ln = len(payload)
    header = bytearray([b0])
    if ln < 126:
        header.append(ln)
    elif ln < 65536:
        header.append(126)
        header.extend(struct.pack(">H", ln))
    else:
        header.append(127)
        header.extend(struct.pack(">Q", ln))
    sock.send(bytes(header) + payload)


def _recv_ws_frame(sock, buf):
    while True:
        if len(buf) < 2:
            more = sock.recv(2048)
            if not more:
                return None, None, buf
            buf += more
        b0 = buf[0]
        b1 = buf[1]
        opcode = b0 & 0x0F
        masked = (b1 >> 7) & 1
        ln = b1 & 0x7F
        off = 2
        if ln == 126:
            while len(buf) < off + 2:
                more = sock.recv(2048)
                if not more:
                    return None, None, buf
                buf += more
            ln = struct.unpack_from(">H", buf, off)[0]
            off += 2
        elif ln == 127:
            while len(buf) < off + 8:
                more = sock.recv(2048)
                if not more:
                    return None, None, buf
                buf += more
            ln = struct.unpack_from(">Q", buf, off)[0]
            off += 8
        mask_key = b""
        if masked:
            while len(buf) < off + 4:
                more = sock.recv(2048)
                if not more:
                    return None, None, buf
                buf += more
            mask_key = buf[off : off + 4]
            off += 4
        while len(buf) < off + ln:
            more = sock.recv(2048)
            if not more:
                return None, None, buf
            buf += more
        payload = bytearray(buf[off : off + ln])
        buf = buf[off + ln :]
        if masked:
            for i in range(len(payload)):
                payload[i] ^= mask_key[i & 3]
        return opcode, bytes(payload), buf


def _handle_json_command(text):
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return {"ok": False, "error": "invalid_json"}
    if not isinstance(obj, dict):
        return {"ok": False, "error": "expected_object"}
    action = obj.get("action")
    if action == "turn_on":
        return {"ok": True, "action": "turn_on"}
    if action == "turn_off":
        return {"ok": True, "action": "turn_off"}
    if action == "status":
        return {"ok": True, "action": "status", "device": "esp32"}
    return {"ok": False, "error": "unknown_action", "action": action}


def _serve_client(sock):
    headers, buf = _recv_http_headers(sock)
    if not headers:
        sock.close()
        return
    key = headers.get("sec-websocket-key")
    if not key:
        sock.close()
        return
    _send_handshake(sock, key)
    try:
        while True:
            opcode, payload, buf = _recv_ws_frame(sock, buf)
            if opcode is None:
                break
            if opcode == 0x8:
                break
            if opcode == 0x9:
                _send_ws_frame(sock, 0xA, payload)
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                try:
                    text = payload.decode("utf-8")
                except UnicodeError:
                    reply = {"ok": False, "error": "invalid_utf8"}
                else:
                    reply = _handle_json_command(text)
                _send_ws_frame(sock, 0x1, json.dumps(reply).encode("utf-8"))
            elif opcode == 0x0:
                continue
            else:
                break
    finally:
        try:
            sock.close()
        except OSError:
            pass


def main():
    connect_wifi()
    addr = socket.getaddrinfo("0.0.0.0", PORT)[0][-1]
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(addr)
    srv.listen(4)
    while True:
        client, _ = srv.accept()
        try:
            _serve_client(client)
        except OSError:
            try:
                client.close()
            except OSError:
                pass


if __name__ == "__main__":
    main()
