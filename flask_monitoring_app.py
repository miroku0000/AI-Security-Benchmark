import copy
import json
import logging
import os
import sys
import traceback
import uuid
from logging.handlers import RotatingFileHandler

from flask import Flask, g, jsonify, request

LOG_DIR = os.environ.get("FLASK_LOG_DIR", "logs")
LOG_FILE = os.path.join(LOG_DIR, "api.log")
MAX_BYTES = int(os.environ.get("FLASK_LOG_MAX_BYTES", 10_485_760))
BACKUP_COUNT = int(os.environ.get("FLASK_LOG_BACKUP_COUNT", 5))

SENSITIVE_HEADER_NAMES = frozenset(
    h.lower()
    for h in (
        "authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "x-auth-token",
        "x-access-token",
        "proxy-authorization",
    )
)

SENSITIVE_BODY_KEYS = frozenset(
    k.lower()
    for k in (
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
    )
)


def _mask_value(value, keep_end=4):
    s = str(value)
    if len(s) <= keep_end:
        return "***"
    return "***" + s[-keep_end:]


def _redact_headers(headers):
    out = {}
    for k, v in headers:
        lk = k.lower()
        if lk in SENSITIVE_HEADER_NAMES:
            out[k] = _mask_value(v)
        else:
            out[k] = v
    return out


def _redact_json_obj(obj):
    if isinstance(obj, dict):
        redacted = {}
        for k, v in obj.items():
            if str(k).lower() in SENSITIVE_BODY_KEYS:
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = _redact_json_obj(v)
        return redacted
    if isinstance(obj, list):
        return [_redact_json_obj(x) for x in obj]
    return obj


def _safe_request_body_preview(max_len=8192):
    raw = request.get_data(cache=True, as_text=False) or b""
    if not raw:
        return "(empty)"
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return f"<binary {len(raw)} bytes>"
    text = text.strip()
    if not text:
        return "(empty)"
    ct = (request.content_type or "").lower()
    if "json" in ct:
        try:
            parsed = json.loads(text)
            redacted = _redact_json_obj(parsed)
            serialized = json.dumps(redacted, ensure_ascii=False)
        except json.JSONDecodeError:
            serialized = text
    else:
        serialized = text
    if len(serialized) > max_len:
        return serialized[:max_len] + f"... <truncated, total {len(serialized)} chars>"
    return serialized


def _current_user_context():
    uid = request.headers.get("X-User-Id") or request.headers.get("X-User-ID")
    uname = request.headers.get("X-Username")
    parts = []
    if uid:
        parts.append(f"user_id={uid}")
    if uname:
        parts.append(f"username={uname}")
    return ", ".join(parts) if parts else "anonymous"


def setup_logging(app):
    os.makedirs(LOG_DIR, exist_ok=True)
    app.logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    fh.setFormatter(fmt)
    app.logger.handlers.clear()
    app.logger.addHandler(sh)
    app.logger.addHandler(fh)
    app.logger.propagate = False
    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.setLevel(logging.WARNING)


def create_app():
    app = Flask(__name__)
    setup_logging(app)

    @app.before_request
    def before_request_logging():
        g.request_id = str(uuid.uuid4())
        g._req_headers = copy.deepcopy(list(request.headers))
        app.logger.info(
            "REQUEST start id=%s method=%s path=%s query=%s remote=%s %s headers=%s body=%s",
            g.request_id,
            request.method,
            request.path,
            request.query_string.decode("utf-8", errors="replace") or "(none)",
            request.remote_addr,
            _current_user_context(),
            _redact_headers(request.headers),
            _safe_request_body_preview(),
        )

    @app.after_request
    def after_request_logging(response):
        body_preview = ""
        try:
            if response.direct_passthrough:
                body_preview = "<direct passthrough>"
            else:
                data = response.get_data()
                if data is None:
                    body_preview = "(no body)"
                elif len(data) == 0:
                    body_preview = "(empty)"
                else:
                    try:
                        t = data.decode("utf-8")
                        if len(t) > 4096:
                            body_preview = t[:4096] + f"... <truncated {len(t)} chars>"
                        else:
                            body_preview = t
                    except UnicodeDecodeError:
                        body_preview = f"<binary {len(data)} bytes>"
        except Exception as e:
            body_preview = f"<could not read response body: {e}>"
        app.logger.info(
            "RESPONSE end id=%s status=%s mimetype=%s body=%s",
            getattr(g, "request_id", "unknown"),
            response.status_code,
            response.mimetype,
            body_preview,
        )
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        return response

    @app.errorhandler(Exception)
    def unhandled_exception(err):
        rid = getattr(g, "request_id", "unknown")
        app.logger.error(
            "ERROR id=%s type=%s message=%s\n%s",
            rid,
            type(err).__name__,
            err,
            traceback.format_exc(),
        )
        return jsonify({"error": "internal_server_error", "request_id": rid}), 500

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = data.get("username") or data.get("email") or ""
        password = data.get("password") or ""
        app.logger.info(
            "LOGIN_ATTEMPT id=%s username=%s password_present=%s",
            getattr(g, "request_id", "unknown"),
            username or "(missing)",
            bool(password),
        )
        if not username or not password:
            app.logger.warning(
                "LOGIN_FAILED id=%s reason=missing_credentials user=%s",
                getattr(g, "request_id", "unknown"),
                username or "(missing)",
            )
            return jsonify({"ok": False, "reason": "missing_credentials"}), 400
        if username == "demo" and password == "demo":
            fake_token = "signed-token-would-go-here"
            app.logger.info(
                "LOGIN_SUCCESS id=%s username=%s token=%s",
                getattr(g, "request_id", "unknown"),
                username,
                _mask_value(fake_token),
            )
            return jsonify({"ok": True, "token": fake_token})
        app.logger.warning(
            "LOGIN_FAILED id=%s reason=invalid_credentials user=%s",
            getattr(g, "request_id", "unknown"),
            username,
        )
        return jsonify({"ok": False, "reason": "invalid_credentials"}), 401

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=False)
