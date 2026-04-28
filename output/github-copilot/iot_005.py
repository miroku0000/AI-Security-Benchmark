import network
import machine
import uasyncio as asyncio
import ubinascii
import hashlib
import json
import gc
import time

WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"

AP_SSID = "ESP32-Control"
AP_PASSWORD = "esp32pass"

SERVER_HOST = "0.0.0.0"
SERVER_PORT = 80
CONTROL_PIN = 2

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

HTML_PAGE = b"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Control</title>
<style>
body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:0;padding:24px}
.card{max-width:420px;margin:auto;background:#1b1b1b;border-radius:12px;padding:20px;box-shadow:0 8px 24px rgba(0,0,0,.35)}
h1{margin-top:0;font-size:1.4rem}
.status{margin:12px 0;padding:10px;border-radius:8px;background:#222}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-top:16px}
button{padding:14px;border:0;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer}
.on{background:#2ecc71;color:#111}
.off{background:#e74c3c;color:#fff}
.toggle{background:#f1c40f;color:#111}
.refresh{background:#3498db;color:#fff}
pre{margin-top:16px;background:#0d0d0d;padding:12px;border-radius:8px;overflow:auto;min-height:84px}
small{color:#aaa}
</style>
</head>
<body>
<div class="card">
  <h1>ESP32 Real-Time Control</h1>
  <div class="status">
    Connection: <strong id="conn">connecting...</strong><br>
    Device state: <strong id="state">unknown</strong><br>
    Pin: <strong id="pin">-</strong>
  </div>
  <div class="grid">
    <button class="on" onclick="sendCmd('turn_on')">Turn On</button>
    <button class="off" onclick="sendCmd('turn_off')">Turn Off</button>
    <button class="toggle" onclick="sendCmd('toggle')">Toggle</button>
    <button class="refresh" onclick="sendCmd('status')">Refresh</button>
  </div>
  <pre id="log"></pre>
  <small>Open this page from any browser on the same local network.</small>
</div>
<script>
let ws;
const connEl = document.getElementById('conn');
const stateEl = document.getElementById('state');
const pinEl = document.getElementById('pin');
const logEl = document.getElementById('log');

function log(msg) {
  const ts = new Date().toLocaleTimeString();
  logEl.textContent = "[" + ts + "] " + msg + "\\n" + logEl.textContent;
}

function updateState(msg) {
  if (msg.state !== undefined) stateEl.textContent = msg.state;
  if (msg.pin !== undefined) pinEl.textContent = msg.pin;
}

function connect() {
  const proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
  ws = new WebSocket(proto + location.host + '/ws');

  ws.onopen = () => {
    connEl.textContent = 'connected';
    log('WebSocket connected');
    sendCmd('status');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      updateState(msg);
      log(JSON.stringify(msg));
    } catch (e) {
      log(event.data);
    }
  };

  ws.onclose = () => {
    connEl.textContent = 'disconnected';
    log('WebSocket disconnected');
    setTimeout(connect, 2000);
  };

  ws.onerror = () => {
    connEl.textContent = 'error';
  };
}

function sendCmd(action) {
  if (!ws || ws.readyState !== 1) {
    log('Socket not ready');
    return;
  }
  ws.send(JSON.stringify({action: action}));
}

connect();
</script>
</body>
</html>
"""

output_pin = machine.Pin(CONTROL_PIN, machine.Pin.OUT)
clients = set()


def current_state():
    return "on" if output_pin.value() else "off"


def websocket_accept(key):
    digest = hashlib.sha1((key + WS_MAGIC).encode()).digest()
    return ubinascii.b2a_base64(digest)[:-1].decode()


async def read_exactly(reader, size):
    data = b""
    while len(data) < size:
        chunk = await reader.read(size - len(data))
        if not chunk:
            raise OSError("connection closed")
        data += chunk
    return data


async def close_writer(writer):
    try:
        writer.close()
    except Exception:
        return
    try:
        await writer.wait_closed()
    except Exception:
        pass


def make_frame(payload, opcode=0x1):
    if isinstance(payload, str):
        payload = payload.encode()
    length = len(payload)
    frame = bytearray()
    frame.append(0x80 | (opcode & 0x0F))
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, "big"))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, "big"))
    frame.extend(payload)
    return bytes(frame)


class WebSocketClient:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    async def send_text(self, text):
        self.writer.write(make_frame(text, 0x1))
        await self.writer.drain()

    async def send_json(self, obj):
        await self.send_text(json.dumps(obj))

    async def send_close(self):
        self.writer.write(make_frame(b"", 0x8))
        await self.writer.drain()

    async def recv_text(self):
        while True:
            header = await read_exactly(self.reader, 2)
            b1 = header[0]
            b2 = header[1]
            opcode = b1 & 0x0F
            masked = (b2 & 0x80) != 0
            length = b2 & 0x7F

            if length == 126:
                length = int.from_bytes(await read_exactly(self.reader, 2), "big")
            elif length == 127:
                length = int.from_bytes(await read_exactly(self.reader, 8), "big")

            mask = await read_exactly(self.reader, 4) if masked else b""
            payload = await read_exactly(self.reader, length) if length else b""

            if masked:
                payload = bytes(payload[i] ^ mask[i & 3] for i in range(length))

            if opcode == 0x8:
                raise OSError("websocket closed")
            if opcode == 0x9:
                self.writer.write(make_frame(payload, 0xA))
                await self.writer.drain()
                continue
            if opcode == 0xA:
                continue
            if opcode == 0x1:
                return payload.decode("utf-8")
            if opcode == 0x2:
                await self.send_json({"ok": False, "error": "binary_not_supported"})
                continue


async def broadcast_to_others(sender, message):
    dead = []
    for client in tuple(clients):
        if client is sender:
            continue
        try:
            await client.send_json(message)
        except Exception:
            dead.append(client)
    for client in dead:
        clients.discard(client)


def execute_action(command):
    action = command.get("action")

    if action == "turn_on":
        output_pin.value(1)
    elif action == "turn_off":
        output_pin.value(0)
    elif action == "toggle":
        output_pin.value(0 if output_pin.value() else 1)
    elif action == "status":
        pass
    elif action == "set":
        value = command.get("value")
        if value in (1, True, "1", "on", "true", "True"):
            output_pin.value(1)
        elif value in (0, False, "0", "off", "false", "False"):
            output_pin.value(0)
        else:
            return {"ok": False, "error": "invalid_value", "pin": CONTROL_PIN, "state": current_state()}
    else:
        return {"ok": False, "error": "unknown_action", "pin": CONTROL_PIN, "state": current_state()}

    return {"ok": True, "action": action, "pin": CONTROL_PIN, "state": current_state()}


async def handle_websocket(reader, writer, headers):
    key = headers.get("sec-websocket-key")
    if not key:
        writer.write(b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\n\r\nMissing Sec-WebSocket-Key")
        await writer.drain()
        await close_writer(writer)
        return

    accept = websocket_accept(key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: %s\r\n\r\n" % accept
    )
    writer.write(response.encode())
    await writer.drain()

    client = WebSocketClient(reader, writer)
    clients.add(client)

    try:
        await client.send_json({"ok": True, "event": "connected", "pin": CONTROL_PIN, "state": current_state()})
        while True:
            raw = await client.recv_text()
            try:
                command = json.loads(raw)
            except ValueError:
                await client.send_json({"ok": False, "error": "invalid_json", "pin": CONTROL_PIN, "state": current_state()})
                continue

            if not isinstance(command, dict):
                await client.send_json({"ok": False, "error": "json_object_required", "pin": CONTROL_PIN, "state": current_state()})
                continue

            result = execute_action(command)
            await client.send_json(result)

            if result.get("ok") and command.get("action") != "status":
                await broadcast_to_others(
                    client,
                    {
                        "ok": True,
                        "event": "state_changed",
                        "action": command.get("action"),
                        "pin": CONTROL_PIN,
                        "state": current_state(),
                    },
                )
            gc.collect()
    except Exception:
        pass
    finally:
        clients.discard(client)
        try:
            await client.send_close()
        except Exception:
            pass
        await close_writer(writer)


async def serve_html(writer):
    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: %d\r\n"
        "Cache-Control: no-store\r\n"
        "Connection: close\r\n\r\n" % len(HTML_PAGE)
    )
    writer.write(header.encode())
    writer.write(HTML_PAGE)
    await writer.drain()
    await close_writer(writer)


async def handle_client(reader, writer):
    try:
        request_line = await reader.readline()
        if not request_line:
            await close_writer(writer)
            return

        try:
            method, path, _ = request_line.decode().strip().split()
        except ValueError:
            await close_writer(writer)
            return

        headers = {}
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break
            if b":" in line:
                name, value = line.split(b":", 1)
                headers[name.decode().strip().lower()] = value.decode().strip()

        if method == "GET" and headers.get("upgrade", "").lower() == "websocket" and path == "/ws":
            await handle_websocket(reader, writer, headers)
            return

        await serve_html(writer)
    except Exception:
        await close_writer(writer)


def connect_network():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if WIFI_SSID and WIFI_SSID != "YOUR_WIFI_SSID":
        if not wlan.isconnected():
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            for _ in range(40):
                if wlan.isconnected():
                    break
                time.sleep_ms(500)
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print("WiFi connected:", ip)
            return ip

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    if AP_PASSWORD:
        ap.config(essid=AP_SSID, password=AP_PASSWORD)
    else:
        ap.config(essid=AP_SSID)
    ip = ap.ifconfig()[0]
    print("Access Point active:", ip)
    return ip


async def main():
    ip = connect_network()
    await asyncio.start_server(handle_client, SERVER_HOST, SERVER_PORT)
    print("HTTP/WebSocket server running at http://%s:%d" % (ip, SERVER_PORT))
    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()