import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

import functions_framework
from flask import Request

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _verify_signature(raw_body: bytes, signature_header: str | None, secret: str) -> bool:
    if not signature_header:
        return False
    sig = signature_header.strip()
    if sig.startswith("sha256="):
        sig = sig[7:]
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return _constant_time_equals(sig, expected)


def _verify_bearer(auth_header: str | None, expected_token: str) -> bool:
    if not auth_header or not expected_token:
        return False
    parts = auth_header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return False
    return _constant_time_equals(parts[1].strip(), expected_token)


def _parse_timestamp(ts_header: str | None, max_skew_sec: int) -> tuple[bool, str | None]:
    if not ts_header:
        return True, None
    try:
        ts = int(ts_header.strip())
    except ValueError:
        return False, "invalid_timestamp"
    now = int(time.time())
    if abs(now - ts) > max_skew_sec:
        return False, "timestamp_skew"
    return True, None


@functions_framework.http
def payment_webhook(request: Request):
    max_bytes = int(os.environ.get("MAX_BODY_BYTES", "1048576"))
    raw = request.get_data(cache=False, as_text=False)
    if len(raw) > max_bytes:
        return (json.dumps({"ok": False, "error": "payload_too_large"}), 413, {"Content-Type": "application/json"})

    secret = os.environ.get("WEBHOOK_SECRET", "")
    if not secret:
        logger.error("WEBHOOK_SECRET is not configured")
        return (json.dumps({"ok": False, "error": "server_misconfigured"}), 500, {"Content-Type": "application/json"})

    bearer_token = os.environ.get("WEBHOOK_BEARER_TOKEN", "").strip()
    auth_ok = bool(bearer_token) and _verify_bearer(request.headers.get("Authorization"), bearer_token)
    sig_ok = _verify_signature(raw, request.headers.get("X-Webhook-Signature"), secret)

    if not auth_ok and not sig_ok:
        return (json.dumps({"ok": False, "error": "unauthorized"}), 401, {"Content-Type": "application/json"})

    max_skew = int(os.environ.get("WEBHOOK_MAX_TIMESTAMP_SKEW_SEC", "300"))
    ts_ok, ts_err = _parse_timestamp(request.headers.get("X-Webhook-Timestamp"), max_skew)
    if not ts_ok:
        return (
            json.dumps({"ok": False, "error": ts_err or "timestamp_rejected"}),
            401,
            {"Content-Type": "application/json"},
        )

    if not raw:
        return (json.dumps({"ok": False, "error": "empty_body"}), 400, {"Content-Type": "application/json"})

    try:
        payload: Any = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return (json.dumps({"ok": False, "error": "invalid_json"}), 400, {"Content-Type": "application/json"})

    event_type = None
    if isinstance(payload, dict):
        event_type = payload.get("type") or payload.get("event_type")

    idempotency_key = request.headers.get("X-Idempotency-Key") or request.headers.get("Idempotency-Key")

    logger.info(
        "webhook_received",
        extra={
            "event_type": event_type,
            "idempotency_key": idempotency_key,
            "content_type": request.headers.get("Content-Type"),
        },
    )

    result = {
        "ok": True,
        "received": True,
        "event_type": event_type,
        "idempotency_key": idempotency_key,
    }
    return (json.dumps(result), 200, {"Content-Type": "application/json"})

functions-framework==3.8.2