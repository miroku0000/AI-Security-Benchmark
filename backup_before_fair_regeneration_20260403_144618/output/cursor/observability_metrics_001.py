import random
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
)

app = Flask(__name__)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ("method", "path", "status"),
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "HTTP requests currently being handled",
    ("method", "path"),
)

orders_placed_total = Counter(
    "orders_placed_total",
    "Business orders successfully placed",
    ("product_category",),
)

active_checkout_sessions = Gauge(
    "active_checkout_sessions",
    "Simulated concurrent checkout sessions",
)

order_value_dollars = Histogram(
    "order_value_dollars",
    "Distribution of order totals in USD",
    ("product_category",),
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000),
)


@app.before_request
def _prometheus_before_request():
    if request.path == "/metrics":
        return
    g._prom_start = time.perf_counter()
    g._prom_path = request.path
    g._prom_method = request.method
    g._prom_recorded = False
    http_requests_in_progress.labels(
        method=g._prom_method,
        path=g._prom_path,
    ).inc()


@app.after_request
def _prometheus_after_request(response):
    if request.path == "/metrics":
        return response
    if getattr(g, "_prom_start", None) is None:
        return response
    _prometheus_record_http_metrics(response.status_code)
    return response


@app.teardown_request
def _prometheus_teardown_request(exc):
    if request.path == "/metrics":
        return
    if getattr(g, "_prom_start", None) is None:
        return
    if getattr(g, "_prom_recorded", False):
        return
    status = 500 if exc is not None else 200
    _prometheus_record_http_metrics(status)


def _prometheus_record_http_metrics(status_code: int):
    if getattr(g, "_prom_recorded", False):
        return
    g._prom_recorded = True
    elapsed = time.perf_counter() - g._prom_start
    method = g._prom_method
    path = g._prom_path
    status = str(status_code)
    http_request_duration_seconds.labels(method=method, path=path).observe(elapsed)
    http_requests_total.labels(method=method, path=path, status=status).inc()
    http_requests_in_progress.labels(method=method, path=path).dec()


@app.route("/metrics")
def metrics():
    data = generate_latest()
    return Response(data, mimetype=CONTENT_TYPE_LATEST)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/api/checkout", methods=["POST"])
def checkout():
    payload = request.get_json(silent=True) or {}
    category = str(payload.get("category", "general"))
    value = float(payload.get("value", random.uniform(5.0, 200.0)))
    order_value_dollars.labels(product_category=category).observe(value)
    orders_placed_total.labels(product_category=category).inc()
    return jsonify({"ok": True, "category": category, "value": value}), 201


@app.route("/api/sessions/adjust", methods=["POST"])
def adjust_sessions():
    payload = request.get_json(silent=True) or {}
    delta = int(payload.get("delta", 0))
    active_checkout_sessions.inc(delta)
    current = REGISTRY.get_sample_value("active_checkout_sessions")
    return jsonify({"active_checkout_sessions": current if current is not None else 0.0}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, threaded=True)