import network
import socket
import struct
import json
import hashlib
import binascii
import machine
import time


SSID = "YOUR_WIFI_SSID"
PASSWORD = "YOUR_WIFI_PASSWORD"
PORT = 8080

WEBSOCKET_MAGIC = "258EAFA5-E914-47DA-95CA-5AB5DC852E59"


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
    print("Connected:", wlan.ifconfig())
    return wlan.ifconfig()[0]


def parse_http_request(data):
    headers = {}
    lines = data.decode("utf-8").split("\r\n")
    request_line = lines[0]
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value
    return request_line, headers


def compute_accept_key(ws_key):
    raw = ws_key.strip() + WEBSOCKET_MAGIC
    sha1 = hashlib.sha1(raw.encode()).digest()
    return binascii.b2a_base64(sha1).decode().strip()


def do_handshake(client, headers):
    ws_key = headers.get("sec-websocket-key", "")
    accept_key = compute_accept_key(ws_key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: " + accept_key + "\r\n"
        "\r\n"
    )
    client.send(response.encode())


def read_frame(client):
    header = client.recv(2)
    if len(header) < 2:
        return None, None

    opcode = header[0] & 0x0F
    masked = (header[1] & 0x80) != 0
    length = header[1] & 0x7F

    if length == 126:
        raw = client.recv(2)
        length = struct.unpack(">H", raw)[0]
    elif length == 127:
        raw = client.recv(8)
        length = struct.unpack(">Q", raw)[0]

    mask_key = client.recv(4) if masked else None

    payload = b""
    while len(payload) < length:
        chunk = client.recv(min(length - len(payload), 1024))
        if not chunk:
            break
        payload += chunk

    if masked and mask_key:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))

    return opcode, payload


def send_frame(client, data, opcode=0x01):
    payload = data.encode("utf-8") if isinstance(data, str) else data
    frame = bytearray()
    frame.append(0x80 | opcode)

    length = len(payload)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(127)
        frame.extend(struct.pack(">Q", length))

    frame.extend(payload)
    client.send(frame)


def send_close(client, code=1000):
    payload = struct.pack(">H", code)
    send_frame(client, payload, opcode=0x08)


def handle_command(command):
    action = command.get("action", "")
    target = command.get("target", "device")
    value = command.get("value", None)

    if action == "turn_on":
        return {"status": "ok", "action": "turn_on", "target": target, "state": "on"}
    elif action == "turn_off":
        return {"status": "ok", "action": "turn_off", "target": target, "state": "off"}
    elif action == "set_value":
        if value is not None:
            return {"status": "ok", "action": "set_value", "target": target, "value": value}
        return {"status": "error", "message": "missing value parameter"}
    elif action == "status":
        return {"status": "ok", "action": "status", "uptime_ms": time.ticks_ms(), "free_mem": __import__("gc").mem_free()}
    elif action == "restart":
        return {"status": "ok", "action": "restart", "message": "restarting in 2 seconds"}
    elif action == "ping":
        return {"status": "ok", "action": "pong"}
    else:
        return {"status": "error", "message": "unknown action: " + str(action)}


def handle_websocket(client, addr):
    print("WebSocket connected:", addr)
    try:
        while True:
            opcode, payload = read_frame(client)

            if opcode is None or opcode == 0x08:
                print("Client disconnected:", addr)
                try:
                    send_close(client)
                except Exception:
                    pass
                break

            if opcode == 0x09:
                send_frame(client, payload, opcode=0x0A)
                continue

            if opcode == 0x0A:
                continue

            if opcode == 0x01:
                text = payload.decode("utf-8")
                try:
                    command = json.loads(text)
                except ValueError:
                    response = {"status": "error", "message": "invalid JSON"}
                    send_frame(client, json.dumps(response))
                    continue

                response = handle_command(command)
                send_frame(client, json.dumps(response))

                if command.get("action") == "restart":
                    time.sleep(2)
                    machine.reset()
    except OSError as e:
        print("Connection error:", e)
    finally:
        client.close()


def serve_dashboard(client):
    html = """HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nConnection: close\r\n\r\n<!DOCTYPE html>
<html><head><title>IoT Control</title><style>
body{font-family:sans-serif;max-width:600px;margin:40px auto;padding:20px}
button{padding:10px 20px;margin:5px;font-size:16px;cursor:pointer;border:none;border-radius:4px;color:#fff}
.on{background:#22c55e}.off{background:#ef4444}.status{background:#3b82f6}
#log{background:#111;color:#0f0;padding:15px;margin-top:20px;height:200px;overflow-y:auto;font-family:monospace;font-size:13px;border-radius:4px}
</style></head><body>
<h2>IoT Device Control</h2>
<button class="on" onclick="send({action:'turn_on'})">Turn On</button>
<button class="off" onclick="send({action:'turn_off'})">Turn Off</button>
<button class="status" onclick="send({action:'status'})">Status</button>
<button class="status" onclick="send({action:'ping'})">Ping</button>
<div id="log"></div>
<script>
var ws=new WebSocket('ws://'+location.host+'/ws');
var log=document.getElementById('log');
ws.onmessage=function(e){log.innerHTML+='&lt; '+e.data+'\\n';log.scrollTop=log.scrollHeight};
ws.onopen=function(){log.innerHTML+='Connected\\n'};
ws.onclose=function(){log.innerHTML+='Disconnected\\n'};
function send(o){var s=JSON.stringify(o);ws.send(s);log.innerHTML+='&gt; '+s+'\\n';log.scrollTop=log.scrollHeight}
</script></body></html>"""
    client.send(html.encode())
    client.close()


def main():
    ip = connect_wifi()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(3)
    print("WebSocket server running on ws://{}:{}".format(ip, PORT))
    print("Dashboard at http://{}:{}".format(ip, PORT))

    while True:
        client, addr = server.accept()
        try:
            data = client.recv(1024)
            if not data:
                client.close()
                continue

            request_line, headers = parse_http_request(data)

            if "upgrade" in headers.get("connection", "").lower() and headers.get("upgrade", "").lower() == "websocket":
                do_handshake(client, headers)
                handle_websocket(client, addr)
            elif "GET / " in request_line or "GET /index" in request_line:
                serve_dashboard(client)
            else:
                client.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
                client.close()
        except Exception as e:
            print("Error:", e)
            try:
                client.close()
            except Exception:
                pass


if __name__ == "__main__":
    main()