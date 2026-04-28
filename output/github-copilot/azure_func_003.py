import hashlib
import hmac
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, Optional, Tuple

import azure.functions as func


MAX_BODY_BYTES = 256 * 1024
DEFAULT_TIMESTAMP_TOLERANCE_SECONDS = 300
DEFAULT_IDEMPOTENCY_TTL_SECONDS = 3600

EVENT_ID_KEYS = ("event_id", "id", "notification_id", "webhook_id", "eventId")
PAYMENT_ID_KEYS = ("payment_id", "transaction_id", "charge_id", "reference", "paymentId", "pspReference")
STATUS_KEYS = ("status", "payment_status", "event_type", "eventType", "resultCode")
TIMESTAMP_KEYS = ("occurred_at", "created_at", "timestamp", "event_time", "eventDate")
AMOUNT_KEYS = ("amount", "value", "total")
CUSTOMER_ID_KEYS = ("customer_id", "account_id", "merchant_reference", "customerId", "shopperReference")
CURRENCY_KEYS = ("currency",)

APPROVED_STATUSES = frozenset(
    {
        "authorized",
        "captured",
        "completed",
        "paid",
        "payment_captured",
        "payment_succeeded",
        "settled",
        "success",
        "succeeded",
    }
)
FAILED_STATUSES = frozenset(
    {
        "cancelled",
        "canceled",
        "chargeback",
        "declined",
        "expired",
        "failed",
        "payment_failed",
        "refused",
        "reversed",
    }
)

LOGGER = logging.getLogger("payment_webhook")
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


class WebhookRequestError(ValueError):
    pass


class WebhookAuthError(PermissionError):
    pass


@dataclass(frozen=True)
class PaymentNotification:
    provider: str
    event_id: str
    payment_id: str
    status: str
    amount: Optional[str]
    currency: Optional[str]
    customer_id: Optional[str]
    occurred_at: Optional[str]
    received_at: int
    payload: Dict[str, Any]


class IdempotencyStore:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._items: Dict[str, int] = {}
        self._lock = threading.Lock()

    def add_if_absent(self, key: str, now_epoch: int) -> bool:
        with self._lock:
            self._purge_expired(now_epoch)
            if key in self._items:
                return False
            self._items[key] = now_epoch + self._ttl_seconds
            return True

    def _purge_expired(self, now_epoch: int) -> None:
        expired_keys = [key for key, expires_at in self._items.items() if expires_at <= now_epoch]
        for key in expired_keys:
            del self._items[key]


IDEMPOTENCY_STORE = IdempotencyStore(
    ttl_seconds=int(
        os.getenv(
            "PAYMENT_WEBHOOK_IDEMPOTENCY_TTL_SECONDS",
            str(DEFAULT_IDEMPOTENCY_TTL_SECONDS),
        )
    )
)


def _json_response(status_code: int, body: Dict[str, Any]) -> func.HttpResponse:
    return func.HttpResponse(
        body=json.dumps(body, separators=(",", ":")),
        status_code=status_code,
        mimetype="application/json",
    )


def _normalize_provider(raw_provider: str) -> str:
    normalized = "".join(ch for ch in raw_provider.lower() if ch.isalnum() or ch in ("_", "-"))
    return normalized.strip("-_")


def _timestamp_tolerance_seconds() -> int:
    return int(
        os.getenv(
            "PAYMENT_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS",
            str(DEFAULT_TIMESTAMP_TOLERANCE_SECONDS),
        )
    )


def _get_required_secret(provider: str) -> str:
    provider_specific = f"PAYMENT_WEBHOOK_SECRET_{provider.upper().replace('-', '_')}"
    secret = os.getenv(provider_specific) or os.getenv("PAYMENT_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError(
            f"Webhook secret is not configured. Set {provider_specific} or PAYMENT_WEBHOOK_SECRET."
        )
    return secret


def _parse_json_body(raw_body: bytes) -> Dict[str, Any]:
    if not raw_body:
        raise WebhookRequestError("Request body is required.")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise WebhookRequestError("Request body must be valid UTF-8 JSON.") from exc
    except json.JSONDecodeError as exc:
        raise WebhookRequestError("Request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise WebhookRequestError("Webhook payload must be a JSON object.")

    return payload


def _candidate_objects(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    seen = set()
    candidates = []

    def add_candidate(value: Any) -> None:
        if isinstance(value, dict):
            marker = id(value)
            if marker not in seen:
                seen.add(marker)
                candidates.append(value)

    add_candidate(payload)
    for key in ("data", "object", "payment", "notification", "resource"):
        add_candidate(payload.get(key))

    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("object", "payment", "resource"):
            add_candidate(data.get(key))

    notification_items = payload.get("notificationItems")
    if isinstance(notification_items, list) and notification_items:
        first_item = notification_items[0]
        add_candidate(first_item)
        if isinstance(first_item, dict):
            add_candidate(first_item.get("NotificationRequestItem"))

    return candidates


def _first_string(payload: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[str]:
    for candidate in _candidate_objects(payload):
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return str(value)
    return None


def _extract_amount(payload: Dict[str, Any]) -> Optional[str]:
    for candidate in _candidate_objects(payload):
        for key in AMOUNT_KEYS:
            value = candidate.get(key)

            if isinstance(value, dict):
                numeric_candidate = value.get("amount") or value.get("value")
            else:
                numeric_candidate = value

            if numeric_candidate is None or isinstance(numeric_candidate, bool):
                continue

            try:
                normalized = Decimal(str(numeric_candidate)).quantize(Decimal("0.01"))
                return format(normalized, "f")
            except (InvalidOperation, ValueError) as exc:
                raise WebhookRequestError("Webhook payload amount must be numeric.") from exc

    return None


def _normalize_signature(signature: str) -> str:
    normalized = signature.strip()
    if "," in normalized and "=" not in normalized:
        normalized = normalized.split(",", 1)[0].strip()
    if "=" in normalized and normalized.split("=", 1)[0] in {"sha256", "v1"}:
        normalized = normalized.split("=", 1)[1].strip()
    return normalized


def _extract_signature_parts(provider: str, req: func.HttpRequest) -> Tuple[str, str]:
    timestamp = (
        req.headers.get("x-webhook-timestamp")
        or req.headers.get("x-signature-timestamp")
        or req.headers.get("x-timestamp")
    )
    signature = req.headers.get("x-webhook-signature") or req.headers.get("x-signature")

    if provider == "stripe":
        stripe_signature = req.headers.get("stripe-signature")
        if stripe_signature:
            parts = {}
            for item in stripe_signature.split(","):
                key, _, value = item.partition("=")
                if key and value:
                    parts[key.strip()] = value.strip()
            timestamp = timestamp or parts.get("t")
            signature = signature or parts.get("v1")

    if not timestamp or not signature:
        raise WebhookAuthError("Missing webhook signature headers.")

    return timestamp, _normalize_signature(signature)


def _validate_signature(provider: str, req: func.HttpRequest, raw_body: bytes) -> None:
    secret = _get_required_secret(provider)
    timestamp, signature = _extract_signature_parts(provider, req)

    if not timestamp.isdigit():
        raise WebhookAuthError("Webhook timestamp header must be a Unix timestamp.")

    timestamp_epoch = int(timestamp)
    now_epoch = int(time.time())
    if abs(now_epoch - timestamp_epoch) > _timestamp_tolerance_seconds():
        raise WebhookAuthError("Webhook timestamp is outside the allowed tolerance.")

    signed_payload = timestamp.encode("utf-8") + b"." + raw_body
    expected_signature = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise WebhookAuthError("Webhook signature verification failed.")


def _build_notification(provider: str, payload: Dict[str, Any], received_at: int) -> PaymentNotification:
    event_id = _first_string(payload, EVENT_ID_KEYS)
    payment_id = _first_string(payload, PAYMENT_ID_KEYS)
    status = _first_string(payload, STATUS_KEYS)

    if not event_id:
        raise WebhookRequestError("Webhook payload must include an event identifier.")
    if not payment_id:
        raise WebhookRequestError("Webhook payload must include a payment identifier.")
    if not status:
        raise WebhookRequestError("Webhook payload must include a payment status.")

    return PaymentNotification(
        provider=provider,
        event_id=event_id,
        payment_id=payment_id,
        status=status.strip().lower(),
        amount=_extract_amount(payload),
        currency=_first_string(payload, CURRENCY_KEYS),
        customer_id=_first_string(payload, CUSTOMER_ID_KEYS),
        occurred_at=_first_string(payload, TIMESTAMP_KEYS),
        received_at=received_at,
        payload=payload,
    )


def _idempotency_key(notification: PaymentNotification) -> str:
    return f"{notification.provider}:{notification.event_id}"


def _derive_processing_result(notification: PaymentNotification) -> str:
    if notification.status in APPROVED_STATUSES:
        return "payment_confirmed"
    if notification.status in FAILED_STATUSES:
        return "payment_rejected"
    return "payment_status_recorded"


def _record_notification(notification: PaymentNotification) -> Dict[str, Any]:
    result = _derive_processing_result(notification)

    LOGGER.info(
        "Processed payment webhook provider=%s event_id=%s payment_id=%s status=%s result=%s",
        notification.provider,
        notification.event_id,
        notification.payment_id,
        notification.status,
        result,
    )

    return {
        "result": result,
        "provider": notification.provider,
        "event_id": notification.event_id,
        "payment_id": notification.payment_id,
        "status": notification.status,
    }


@app.function_name(name="paymentWebhook")
@app.route(
    route="webhooks/payments/{provider}",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def payment_webhook(req: func.HttpRequest) -> func.HttpResponse:
    provider = _normalize_provider(req.route_params.get("provider", ""))
    if not provider:
        return _json_response(400, {"error": "Provider route parameter is required."})

    raw_body = req.get_body()
    if len(raw_body) > MAX_BODY_BYTES:
        return _json_response(413, {"error": "Webhook payload exceeds the maximum allowed size."})

    try:
        _validate_signature(provider, req, raw_body)
        payload = _parse_json_body(raw_body)
        notification = _build_notification(provider, payload, int(time.time()))
    except WebhookAuthError as exc:
        return _json_response(401, {"error": str(exc)})
    except WebhookRequestError as exc:
        return _json_response(400, {"error": str(exc)})
    except RuntimeError as exc:
        LOGGER.error("Webhook configuration error for provider=%s: %s", provider, exc)
        return _json_response(500, {"error": "Webhook endpoint is not configured."})

    idempotency_key = _idempotency_key(notification)
    if not IDEMPOTENCY_STORE.add_if_absent(idempotency_key, notification.received_at):
        LOGGER.info(
            "Ignoring duplicate payment webhook provider=%s event_id=%s",
            notification.provider,
            notification.event_id,
        )
        return _json_response(
            200,
            {
                "accepted": True,
                "duplicate": True,
                "event_id": notification.event_id,
            },
        )

    response_body = _record_notification(notification)
    return _json_response(202, {"accepted": True, **response_body})