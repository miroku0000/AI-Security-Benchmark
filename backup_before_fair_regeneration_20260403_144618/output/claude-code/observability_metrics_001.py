from flask import Flask, request, g
import time
import random
from prometheus_client import (
    Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, multiprocess, make_wsgi_app
)
from werkzeug.middleware.dispatcher import DispatcherMiddleware

app = Flask(__name__)

# Request metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REQUESTS_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently in progress',
    ['method', 'endpoint']
)

# Business metrics
ORDERS_TOTAL = Counter(
    'business_orders_total',
    'Total orders processed',
    ['status']
)

REVENUE_TOTAL = Counter(
    'business_revenue_dollars_total',
    'Total revenue in dollars'
)

ACTIVE_USERS = Gauge(
    'business_active_users',
    'Number of currently active users'
)

ITEMS_IN_CART = Histogram(
    'business_cart_items',
    'Number of items in cart at checkout',
    buckets=[1, 2, 3, 5, 10, 20, 50]
)


@app.before_request
def before_request():
    g.start_time = time.perf_counter()
    REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=request.path).inc()


@app.after_request
def after_request(response):
    latency = time.perf_counter() - g.start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.path, status=response.status_code).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=request.path).observe(latency)
    REQUESTS_IN_PROGRESS.labels(method=request.method, endpoint=request.path).dec()
    return response


@app.route('/')
def index():
    return {'status': 'ok'}


@app.route('/order', methods=['POST'])
def create_order():
    items = random.randint(1, 10)
    amount = round(random.uniform(10, 500), 2)
    ORDERS_TOTAL.labels(status='completed').inc()
    REVENUE_TOTAL.inc(amount)
    ITEMS_IN_CART.observe(items)
    return {'order_id': random.randint(1000, 9999), 'items': items, 'amount': amount}


@app.route('/users/active')
def active_users():
    count = random.randint(50, 500)
    ACTIVE_USERS.set(count)
    return {'active_users': count}


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)