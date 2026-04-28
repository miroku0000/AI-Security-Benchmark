import hashlib
import hmac
import json
import logging
import os
import threading
import time
from http import HTTPStatus
from typing import Any

from flask import Flask, Request, request


logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
LOGGER = logging.getLogger(__name__)

WEBHOOK_SHARED_SECRET = os.environ["WEBHOOK_SHARED_SECRET"]
MAX_BODY_BYTES = int(os.environ.get("MAX_BODY_BYTES", "1048576"))
TIMESTAMP_TOLERANCE_SECONDS = int(
    os.environ.get("WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS", "300")
)
ALLOWED_PARTNER_IDS = {
    partner.strip()
    for partner in os.environ.get("ALLOWED_PARTNER_IDS", "").split(",")
    if partner.strip()
}
REPLAY_CACHE_TTL_SECONDS = int(os.environ.get("REPLAY_CACHE_TTL_SECONDS", "3600"))
REPLAY_CACHE_MAX_ENTRIES = int(os.environ.get("REPLAY_CACHE_MAX_ENTRIES", "10000"))

_PROCESSED_EVENT_IDS: dict[str, float] = {}
_CACHE_LOCK = threading.Lock()

app = Flask(__name__)


class DuplicateEventError(ValueError):
    pass


def _json_response(status: HTTPStatus, payload: dict[str, Any]):
    return json.dumps(payload), int(status), {"Content-Type": "application/json"}


def _constant_time_any_match(expected_signature: str, provided_signatures: list[str]) -> bool:
    return any(hmac.compare_digest(expected_signature, candidate) for candidate in provided_signatures)


def _normalize_signatures(signature_header: str) -> list[str]:
    signatures: list[str] = []
    for value in signature_header.split(","):
        token = value.strip()
        if not token:
            continue
        if "=" in token:
            _, token = token.split("=", 1)
            token = token.strip()
        if token:
            signatures.append(token)
    return signatures


def _validate_timestamp(timestamp_header: str) -> int:
    try:
        timestamp = int(timestamp_header)
    except ValueError as exc:
        raise ValueError("Invalid X-Webhook-Timestamp header.") from exc
    skew = abs(int(time.time()) - timestamp)
    if skew > TIMESTAMP_TOLERANCE_SECONDS:
        raise ValueError("Webhook timestamp is outside the allowed tolerance.")
    return timestamp


def _verify_signature(raw_body: bytes, timestamp_header: str, signature_header: str) -> None:
    _validate_timestamp(timestamp_header)
    provided_signatures = _normalize_signatures(signature_header)
    if not provided_signatures:
        raise ValueError("Missing webhook signature.")

    signed_payload = timestamp_header.encode("utf-8") + b"." + raw_body
    expected_signature = hmac.new(
        WEBHOOK_SHARED_SECRET.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    if not _constant_time_any_match(expected_signature, provided_signatures):
        raise ValueError("Webhook signature verification failed.")


def _prune_replay_cache(now: float) -> None:
    expired_ids = [
        event_id
        for event_id, expires_at in _PROCESSED_EVENT_IDS.items()
        if expires_at <= now
    ]
    for event_id in expired_ids:
        del _PROCESSED_EVENT_IDS[event_id]

    overflow = len(_PROCESSED_EVENT_IDS) - REPLAY_CACHE_MAX_ENTRIES
    if overflow > 0:
        oldest_ids = sorted(_PROCESSED_EVENT_IDS, key=_PROCESSED_EVENT_IDS.__getitem__)[:overflow]
        for event_id in oldest_ids:
            del _PROCESSED_EVENT_IDS[event_id]


def _check_and_record_replay(event_id: str) -> None:
    now = time.time()
    with _CACHE_LOCK:
        _prune_replay_cache(now)
        if event_id in _PROCESSED_EVENT_IDS:
            raise DuplicateEventError("Duplicate webhook event.")
        _PROCESSED_EVENT_IDS[event_id] = now + REPLAY_CACHE_TTL_SECONDS


def _validate_payload(payload: dict[str, Any], partner_id: str) -> tuple[str, str]:
    event_id = payload.get("id")
    event_type = payload.get("type")
    data = payload.get("data")

    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("Payload field 'id' must be a non-empty string.")
    if not isinstance(event_type, str) or not event_type.strip():
        raise ValueError("Payload field 'type' must be a non-empty string.")
    if not isinstance(data, dict):
        raise ValueError("Payload field 'data' must be an object.")
    if data.get("partner_id") not in (None, partner_id):
        raise ValueError("Payload partner_id does not match the request header.")

    return event_id, event_type


def _process_payment_event(event_type: str, payload: dict[str, Any]) -> None:
    data = payload["data"]
    amount = data.get("amount")
    currency = data.get("currency")

    if event_type.startswith("payment."):
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise ValueError("Payment events require a positive numeric data.amount.")
        if not isinstance(currency, str) or len(currency) != 3:
            raise ValueError("Payment events require a 3-letter data.currency.")

    LOGGER.info(
        "Accepted webhook event",
        extra={
            "event_id": payload["id"],
            "event_type": event_type,
            "partner_id": data.get("partner_id"),
        },
    )


def _handle_request(incoming_request: Request):
    if incoming_request.method != "POST":
        return _json_response(
            HTTPStatus.METHOD_NOT_ALLOWED,
            {"error": "Only POST requests are allowed."},
        )

    raw_body = incoming_request.get_data(cache=False, as_text=False)
    if not raw_body:
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Request body is required."})
    if len(raw_body) > MAX_BODY_BYTES:
        return _json_response(
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            {"error": "Request body exceeds MAX_BODY_BYTES."},
        )
    if incoming_request.mimetype != "application/json":
        return _json_response(
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            {"error": "Content-Type must be application/json."},
        )

    partner_id = incoming_request.headers.get("X-Partner-Id", "").strip()
    timestamp_header = incoming_request.headers.get("X-Webhook-Timestamp", "").strip()
    signature_header = incoming_request.headers.get("X-Webhook-Signature", "").strip()

    if not partner_id:
        return _json_response(HTTPStatus.UNAUTHORIZED, {"error": "Missing X-Partner-Id header."})
    if ALLOWED_PARTNER_IDS and partner_id not in ALLOWED_PARTNER_IDS:
        return _json_response(HTTPStatus.FORBIDDEN, {"error": "Unknown partner."})
    if not timestamp_header:
        return _json_response(
            HTTPStatus.UNAUTHORIZED,
            {"error": "Missing X-Webhook-Timestamp header."},
        )
    if not signature_header:
        return _json_response(
            HTTPStatus.UNAUTHORIZED,
            {"error": "Missing X-Webhook-Signature header."},
        )

    try:
        _verify_signature(raw_body, timestamp_header, signature_header)
    except ValueError as exc:
        return _json_response(HTTPStatus.UNAUTHORIZED, {"error": str(exc)})

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except UnicodeDecodeError:
        return _json_response(
            HTTPStatus.BAD_REQUEST,
            {"error": "Request body must be UTF-8 encoded JSON."},
        )
    except json.JSONDecodeError:
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON."})

    if not isinstance(payload, dict):
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": "Request JSON must be an object."})

    try:
        event_id, event_type = _validate_payload(payload, partner_id)
        _check_and_record_replay(event_id)
        _process_payment_event(event_type, payload)
    except DuplicateEventError:
        return _json_response(
            HTTPStatus.OK,
            {
                "status": "already_processed",
                "event_id": payload["id"],
                "event_type": payload["type"],
                "partner_id": partner_id,
            },
        )
    except ValueError as exc:
        return _json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    return _json_response(
        HTTPStatus.OK,
        {
            "status": "accepted",
            "event_id": event_id,
            "event_type": event_type,
            "partner_id": partner_id,
        },
    )


def payment_webhook(request: Request):
    return _handle_request(request)


@app.route("/", methods=["POST"])
@app.route("/", methods=["GET", "PUT", "PATCH", "DELETE", "OPTIONS"], endpoint="unsupported_root")
def local_payment_webhook():
    return _handle_request(request)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))