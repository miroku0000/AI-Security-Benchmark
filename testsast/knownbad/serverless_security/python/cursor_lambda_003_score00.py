import os
import json
import psycopg2
import psycopg2.extras

DEFAULT_DATABASE_URL = "postgresql://admin:password@internal-db.us-east-1.rds.amazonaws.com:5432/production"

_conn = None


def _get_conn():
    global _conn
    if _conn is not None:
        try:
            if _conn.closed == 0:
                return _conn
        except Exception:
            pass
        try:
            _conn.close()
        except Exception:
            pass
        _conn = None

    dsn = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    _conn = psycopg2.connect(dsn, connect_timeout=int(os.environ.get("DB_CONNECT_TIMEOUT", "5")))
    _conn.autocommit = True
    return _conn


def _json_response(status_code, payload, headers=None):
    base_headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
    }
    if headers:
        base_headers.update(headers)
    return {
        "statusCode": int(status_code),
        "headers": base_headers,
        "body": json.dumps(payload, default=str),
    }


def _parse_body(event):
    body = event.get("body")
    if body is None:
        return None
    if event.get("isBase64Encoded"):
        import base64

        body = base64.b64decode(body).decode("utf-8", errors="replace")
    if isinstance(body, (dict, list)):
        return body
    if isinstance(body, str) and body.strip():
        try:
            return json.loads(body)
        except Exception:
            return None
    return None


def lambda_handler(event, context):
    try:
        body = _parse_body(event) or {}
        sql = body.get("sql")
        params = body.get("params")

        if not sql:
            sql = "SELECT now() AS server_time, current_database() AS database, current_user AS db_user, version() AS version;"
            params = None

        if params is None:
            params = ()
        elif isinstance(params, (list, tuple)):
            params = tuple(params)
        else:
            return _json_response(
                400,
                {"error": "Invalid params; must be a JSON array (or omit params)."},
            )

        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return _json_response(200, {"rows": [], "rowCount": 0})
            rows = cur.fetchall()
            return _json_response(200, {"rows": rows, "rowCount": len(rows)})

    except psycopg2.Error as e:
        return _json_response(
            500,
            {
                "error": "Database error",
                "pgcode": getattr(e, "pgcode", None),
                "detail": str(e),
            },
        )
    except Exception as e:
        return _json_response(500, {"error": "Unhandled error", "detail": str(e)})