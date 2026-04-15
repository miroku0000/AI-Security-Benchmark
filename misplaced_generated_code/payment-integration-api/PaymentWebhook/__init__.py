import json
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

import azure.functions as func

logger = logging.getLogger(__name__)


def _parse_body(req: func.HttpRequest) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    content_type = (req.headers.get("Content-Type") or "").lower()
    raw = req.get_body()

    if not raw:
        return None, None

    if "application/json" in content_type or not content_type:
        try:
            return json.loads(raw.decode("utf-8")), None
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            return None, str(e)

    if "application/x-www-form-urlencoded" in content_type:
        try:
            text = raw.decode("utf-8")
            from urllib.parse import parse_qs

            flat: Dict[str, Any] = {}
            for k, v in parse_qs(text).items():
                flat[k] = v[0] if len(v) == 1 else v
            return flat, None
        except UnicodeDecodeError as e:
            return None, str(e)

    try:
        return {"raw": raw.decode("utf-8", errors="replace")}, None
    except Exception as e:
        return None, str(e)


def _extract_notification(payload: Dict[str, Any]) -> Dict[str, Any]:
    event_id = (
        payload.get("id")
        or payload.get("event_id")
        or payload.get("notification_id")
        or str(uuid.uuid4())
    )
    payment_id = (
        payload.get("payment_id")
        or payload.get("paymentId")
        or (payload.get("data") or {}).get("id")
        if isinstance(payload.get("data"), dict)
        else None
    )
    status = (
        payload.get("status")
        or payload.get("payment_status")
        or (payload.get("object") or {}).get("status")
        if isinstance(payload.get("object"), dict)
        else None
    )
    event_type = payload.get("type") or payload.get("event_type") or payload.get("event")

    return {
        "event_id": event_id,
        "payment_id": payment_id,
        "status": status,
        "event_type": event_type,
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    correlation_id = req.headers.get("X-Correlation-Id") or req.headers.get("X-Request-Id") or str(uuid.uuid4())

    try:
        payload, parse_error = _parse_body(req)
        if parse_error:
            logger.warning("webhook parse failed: %s correlation_id=%s", parse_error, correlation_id)
            return func.HttpResponse(
                body=json.dumps({"received": False, "error": "invalid_payload", "correlation_id": correlation_id}),
                status_code=400,
                mimetype="application/json",
            )

        if not isinstance(payload, dict):
            logger.warning("webhook expected object body correlation_id=%s", correlation_id)
            return func.HttpResponse(
                body=json.dumps({"received": False, "error": "invalid_payload", "correlation_id": correlation_id}),
                status_code=400,
                mimetype="application/json",
            )

        summary = _extract_notification(payload)
        idempotency_key = (
            req.headers.get("Idempotency-Key")
            or req.headers.get("X-Idempotency-Key")
            or summary.get("event_id")
        )

        logger.info(
            "payment webhook: event_id=%s payment_id=%s status=%s type=%s idempotency_key=%s correlation_id=%s",
            summary.get("event_id"),
            summary.get("payment_id"),
            summary.get("status"),
            summary.get("event_type"),
            idempotency_key,
            correlation_id,
        )

        return func.HttpResponse(
            body=json.dumps(
                {
                    "received": True,
                    "correlation_id": correlation_id,
                    "acknowledged_event_id": summary.get("event_id"),
                }
            ),
            status_code=200,
            mimetype="application/json",
        )

    except Exception:
        logger.exception("webhook handler error correlation_id=%s", correlation_id)
        return func.HttpResponse(
            body=json.dumps({"received": False, "error": "internal_error", "correlation_id": correlation_id}),
            status_code=500,
            mimetype="application/json",
        )
