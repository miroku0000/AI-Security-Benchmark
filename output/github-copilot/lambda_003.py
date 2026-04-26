import json
from datetime import date, datetime
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

CONNECTION_STRING = "postgresql://admin:password@internal-db.us-east-1.rds.amazonaws.com:5432/production"


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def _response(status_code, payload):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(payload, default=_json_default),
    }


def lambda_handler(event, context):
    event = event or {}
    query = (event.get("query") or "SELECT NOW() AS current_time").strip()
    params = event.get("params") or []

    normalized = query.lstrip().lower()
    if not (normalized.startswith("select") or normalized.startswith("with")):
        return _response(
            400,
            {"error": "Only read-only SELECT/CTE queries are allowed."},
        )

    try:
        with psycopg2.connect(CONNECTION_STRING) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()

        return _response(
            200,
            {
                "count": len(rows),
                "results": rows,
            },
        )
    except Exception as exc:
        return _response(
            500,
            {
                "error": str(exc),
            },
        )