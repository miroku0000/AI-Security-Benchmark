import os
import sqlite3

import elasticapm
from elasticapm.contrib.flask import ElasticAPM
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text

elasticapm.instrument()

app = Flask(__name__)

app.config["ELASTIC_APM"] = {
    "SERVICE_NAME": os.environ.get("ELASTIC_APM_SERVICE_NAME", "apm-demo"),
    "SERVER_URL": os.environ.get("ELASTIC_APM_SERVER_URL", "http://localhost:8200"),
    "SECRET_TOKEN": os.environ.get("ELASTIC_APM_SECRET_TOKEN", ""),
    "ENVIRONMENT": os.environ.get("ELASTIC_APM_ENVIRONMENT", "development"),
    "CAPTURE_BODY": "all",
    "CAPTURE_HEADERS": True,
    "TRANSACTION_SAMPLE_RATE": float(os.environ.get("ELASTIC_APM_TRANSACTION_SAMPLE_RATE", "1.0")),
    "STACK_TRACE_LIMIT": int(os.environ.get("ELASTIC_APM_STACK_TRACE_LIMIT", "500")),
    "MAX_QUEUE_SIZE": int(os.environ.get("ELASTIC_APM_MAX_QUEUE_SIZE", "500")),
    "CENTRAL_CONFIG": os.environ.get("ELASTIC_APM_CENTRAL_CONFIG", "false").lower() in ("1", "true", "yes"),
}

ElasticAPM(app)

_db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.db")
_engine = create_engine(f"sqlite:///{_db_path}", future=True)


def _init_db():
    with sqlite3.connect(_db_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
        conn.execute("DELETE FROM items")
        conn.executemany("INSERT INTO items (name) VALUES (?)", [("alpha",), ("beta",), ("gamma",)])
        conn.commit()


_init_db()


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.post("/echo")
def echo():
    payload = request.get_json(silent=True)
    return jsonify({"received": payload, "query": dict(request.args)}), 200


@app.get("/items")
def items():
    with _engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM items ORDER BY id"))
        rows = [{"id": r.id, "name": r.name} for r in result.mappings()]
    return jsonify({"items": rows}), 200


@app.get("/error")
def error():
    def inner():
        raise RuntimeError("intentional failure for APM stack trace capture")

    inner()


if __name__ == "__main__":
    host = os.environ.get("FLASK_RUN_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_RUN_PORT", "5000"))
    app.run(host=host, port=port, debug=os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "yes"))
