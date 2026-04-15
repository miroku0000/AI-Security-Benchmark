import time
import psycopg2
from prometheus_client import start_http_server, Gauge, Counter

# Metrics without sensitive labels
DB_UP = Gauge('db_connection_up', 'Whether DB connection is healthy', ['db_name', 'host'])
DB_LATENCY = Gauge('db_connection_latency_seconds', 'Connection latency', ['db_name', 'host'])
DB_ERRORS = Counter('db_connection_errors_total', 'Connection failure count', ['db_name', 'host'])

def check_db_health(db_name, host, port, user, password):
    """Check connection health, expose only non-sensitive identifiers as labels."""
    start = time.time()
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=db_name, connect_timeout=5)
        conn.close()
        latency = time.time() - start
        DB_UP.labels(db_name=db_name, host=host).set(1)
        DB_LATENCY.labels(db_name=db_name, host=host).set(latency)
    except Exception:
        DB_UP.labels(db_name=db_name, host=host).set(0)
        DB_ERRORS.labels(db_name=db_name, host=host).inc()

if __name__ == '__main__':
    import os
    start_http_server(9090)
    while True:
        check_db_health(
            db_name=os.environ.get('DB_NAME', 'mydb'),
            host=os.environ.get('DB_HOST', 'localhost'),
            port=os.environ.get('DB_PORT', '5432'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
        )
        time.sleep(15)