from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from http.server import HTTPServer, BaseHTTPRequestHandler
import re
import time

# Low-cardinality metrics safe for Prometheus
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "route", "status"],
)

REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "route"],
)

# Normalize paths to route templates to keep cardinality bounded
ROUTE_PATTERNS = [
    (re.compile(r"^/users/[^/]+$"), "/users/{id}"),
    (re.compile(r"^/users/[^/]+/sessions/[^/]+$"), "/users/{id}/sessions/{sid}"),
    (re.compile(r"^/items/[^/]+$"), "/items/{id}"),
]


def normalize_path(path):
    path = path.split("?")[0]
    for pattern, template in ROUTE_PATTERNS:
        if pattern.match(path):
            return template
    return path if len(path) < 50 else "/unknown"


class AppHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        start = time.monotonic()

        if self.path == "/metrics":
            body = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.write(body)
            return

        route = normalize_path(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

        duration = time.monotonic() - start
        REQUEST_COUNT.labels(method="GET", route=route, status="200").inc()
        REQUEST_DURATION.labels(method="GET", route=route).observe(duration)

    def write(self, data):
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8000), AppHandler)
    print("Serving on :8000, metrics at /metrics")
    server.serve_forever()