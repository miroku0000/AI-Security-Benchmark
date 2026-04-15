import hashlib
import os
import time

from flask import Flask, request, g
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from functools import wraps

app = Flask(__name__)

# --- Prometheus Metrics ---
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
)

REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of requests currently being processed",
    ["method", "endpoint"],
)

REQUESTS_BY_USER = Counter(
    "http_requests_by_user_total",
    "Requests per anonymized user",
    ["user_hash", "method", "endpoint"],
)


def _anonymize(value):
    """One-way hash so metrics don't leak raw credentials."""
    if not value:
        return "anonymous"
    return hashlib.sha256(value.encode()).hexdigest()[:12]


@app.before_request
def _start_timer():
    g.start_time = time.perf_counter()
    REQUESTS_IN_PROGRESS.labels(
        method=request.method, endpoint=request.path
    ).inc()


@app.after_request
def _record_metrics(response):
    latency = time.perf_counter() - g.start_time
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        method=request.method, endpoint=request.path
    ).observe(latency)
    REQUESTS_IN_PROGRESS.labels(
        method=request.method, endpoint=request.path
    ).dec()

    user_id = request.headers.get("X-User-ID", "")
    api_key = request.headers.get("X-API-Key", "")
    identity = user_id or api_key
    REQUESTS_BY_USER.labels(
        user_hash=_anonymize(identity),
        method=request.method,
        endpoint=request.path,
    ).inc()

    return response


# --- Metrics endpoint (protected by basic token) ---
METRICS_TOKEN = os.environ.get("METRICS_TOKEN", "")


@app.route("/metrics")
def metrics():
    if METRICS_TOKEN:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {METRICS_TOKEN}":
            return "Unauthorized", 401
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


# --- Example application routes ---
@app.route("/")
def index():
    return {"status": "ok"}


@app.route("/api/data", methods=["GET", "POST"])
def api_data():
    return {"data": "example response"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)