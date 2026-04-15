import os
import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import re

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
MAX_MESSAGE_LENGTH = 10000
ALLOWED_SERVICE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def sanitize_for_log(value):
    """Remove characters that could enable log injection."""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace("\r", "").replace("\n", " ")
    return value


def write_log(level, service, message):
    level = level.upper()
    if level not in VALID_LOG_LEVELS:
        return False, "Invalid log level"

    if not service or not ALLOWED_SERVICE_NAME_PATTERN.match(service):
        return False, "Invalid service name"

    if not message or len(message) > MAX_MESSAGE_LENGTH:
        return False, "Message is empty or exceeds max length"

    safe_service = sanitize_for_log(service)
    safe_message = sanitize_for_log(message)
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"

    log_entry = "[{}] [{}] [{}] {}\n".format(timestamp, level, safe_service, safe_message)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_entry)

    return True, "Logged"


class LogHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/log":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 65536:
            self.send_response(413)
            self.end_headers()
            self.wfile.write(b'{"error": "Payload too large"}')
            return

        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        level = data.get("level", "INFO")
        service = data.get("service", "")
        message = data.get("message", "")

        success, detail = write_log(level, service, message)
        if success:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": detail}).encode())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/logs":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')
            return

        params = urllib.parse.parse_qs(parsed.query)
        lines = int(params.get("lines", ["50"])[0])
        lines = max(1, min(lines, 1000))

        if not os.path.exists(LOG_FILE):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"logs": []}).encode())
            return

        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        recent = all_lines[-lines:]
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"logs": [l.rstrip() for l in recent]}).encode())

    def log_message(self, format, *args):
        pass


def main():
    host = os.environ.get("LOG_HOST", "127.0.0.1")
    port = int(os.environ.get("LOG_PORT", "8080"))
    server = HTTPServer((host, port), LogHandler)
    print("Log server running on {}:{}".format(host, port))
    print("POST /log  - send {\"level\": \"INFO\", \"service\": \"my-svc\", \"message\": \"hello\"}")
    print("GET  /logs - retrieve recent entries (?lines=100)")
    print("Log file: {}".format(LOG_FILE))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()