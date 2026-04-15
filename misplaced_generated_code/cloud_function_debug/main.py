import functools
import json
import logging
import sys
import traceback
from typing import Any, Callable, Optional

import functions_framework
import google.cloud.logging
from flask import Request, Response

google.cloud.logging.Client().setup_logging()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _safe_decode_body(request: Request) -> str:
    try:
        raw = request.get_data(cache=True, as_text=False)
        if not raw:
            return ""
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        return f"<body decode error: {e}>"


def _log_struct(event: str, payload: dict) -> None:
    line = json.dumps({"event": event, **payload}, default=str)
    logger.info(line)


def _log_request_full(request: Request) -> None:
    headers_dict = {k: v for k, v in request.headers.items()}
    _log_struct(
        "request_headers",
        {
            "headers": headers_dict,
            "method": request.method,
            "path": request.path,
            "query_string": request.query_string.decode("utf-8", errors="replace"),
            "remote_addr": request.remote_addr,
            "content_type": request.content_type,
        },
    )
    body_text = _safe_decode_body(request)
    _log_struct("request_body", {"body": body_text, "body_length": len(body_text)})
    auth = request.headers.get("Authorization") or request.headers.get("authorization")
    x_api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
    _log_struct(
        "authentication_context",
        {
            "authorization_header": auth,
            "x_api_key": x_api_key,
        },
    )
    user_email = (
        request.headers.get("X-User-Email")
        or request.headers.get("x-user-email")
        or request.headers.get("X-Goog-Authenticated-User-Email")
    )
    parsed_email: Optional[str] = None
    if request.content_type and "json" in (request.content_type or "").lower():
        try:
            j = json.loads(body_text) if body_text else {}
            if isinstance(j, dict):
                parsed_email = j.get("email") or j.get("user_email")
        except json.JSONDecodeError:
            parsed_email = None
    _log_struct(
        "user_identity",
        {"user_email_headers": user_email, "user_email_json_body": parsed_email},
    )


class LoggingDatabase:
    def __init__(self) -> None:
        self._conn: Optional[Any] = None

    def execute(self, sql: str, params: Optional[tuple] = None) -> list:
        _log_struct(
            "database_query",
            {
                "sql": sql,
                "parameters": list(params) if params is not None else None,
            },
        )
        return []


db = LoggingDatabase()


def with_full_error_logging(f: Callable[..., Response]) -> Callable[..., Response]:
    @functools.wraps(f)
    def wrapper(request: Request) -> Response:
        _log_request_full(request)
        try:
            return f(request)
        except Exception:
            tb = traceback.format_exc()
            _log_struct(
                "unhandled_exception",
                {
                    "stack_trace": tb,
                    "exception_type": sys.exc_info()[0].__name__ if sys.exc_info()[0] else None,
                },
            )
            logger.error("exception_with_traceback", exc_info=True)
            return Response(
                json.dumps({"error": "internal_error", "trace": tb}),
                status=500,
                mimetype="application/json",
            )

    return wrapper


@functions_framework.http
@with_full_error_logging
def debug_http(request: Request) -> Response:
    if request.method == "GET":
        db.execute("SELECT * FROM users WHERE id = %s", (request.args.get("id", ""),))
    elif request.method == "POST":
        try:
            payload = request.get_json(silent=True) or {}
        except Exception:
            payload = {}
        email = payload.get("email") or _safe_decode_body(request)
        db.execute(
            "INSERT INTO audit (email) VALUES (%s)",
            (email,),
        )
    return Response(
        json.dumps({"ok": True}),
        status=200,
        mimetype="application/json",
    )
