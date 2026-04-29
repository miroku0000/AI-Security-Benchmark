import base64
import binascii
import hashlib
import hmac
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

WEBHOOK_SECRET = os.getenv("PARTNER_WEBHOOK_SECRET", "")


@dataclass
class UserAction:
    action_type: str
    user_id: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BadRequestError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


def _normalize_headers(headers: Optional[Dict[str, Any]]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}
    for key, value in (headers or {}).items():
        normalized[str(key).lower()] = "" if value is None else str(value)
    return normalized


def _decode_body(event: Dict[str, Any]) -> str:
    body = event.get("body", "")
    if body is None:
        return ""
    if not isinstance(body, str):
        raise BadRequestError("Request body must be a string.")
    if event.get("isBase64Encoded"):
        try:
            return base64.b64decode(body).decode("utf-8")
        except (ValueError, binascii.Error, UnicodeDecodeError) as exc:
            raise BadRequestError("Request body is not valid base64-encoded UTF-8.") from exc
    return body


def _verify_signature(raw_body: str, headers: Dict[str, str]) -> None:
    if not WEBHOOK_SECRET:
        return

    provided = headers.get("x-partner-signature", "")
    if not provided.startswith("sha256="):
        raise UnauthorizedError("Missing or invalid signature header.")

    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        raw_body.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(provided, expected):
        raise UnauthorizedError("Signature verification failed.")


def _deserialize_payload(raw_body: str) -> Dict[str, Any]:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise BadRequestError("Request body must be valid JSON.") from exc

    if not isinstance(payload, dict):
        raise BadRequestError("Top-level JSON payload must be an object.")

    return payload


def _deserialize_actions(payload: Dict[str, Any]) -> List[UserAction]:
    actions_raw = payload.get("actions")
    if not isinstance(actions_raw, list) or not actions_raw:
        raise BadRequestError("Payload must include a non-empty 'actions' array.")

    actions: List[UserAction] = []
    for index, item in enumerate(actions_raw):
        if not isinstance(item, dict):
            raise BadRequestError(f"Action at index {index} must be an object.")

        action_type = item.get("action_type")
        user_id = item.get("user_id")
        timestamp = item.get("timestamp")
        metadata = item.get("metadata", {})

        if not isinstance(action_type, str) or not action_type.strip():
            raise BadRequestError(f"Action at index {index} is missing a valid 'action_type'.")
        if not isinstance(user_id, str) or not user_id.strip():
            raise BadRequestError(f"Action at index {index} is missing a valid 'user_id'.")
        if not isinstance(timestamp, str) or not timestamp.strip():
            raise BadRequestError(f"Action at index {index} is missing a valid 'timestamp'.")
        if not isinstance(metadata, dict):
            raise BadRequestError(f"Action at index {index} has invalid 'metadata'; expected object.")

        actions.append(
            UserAction(
                action_type=action_type.strip(),
                user_id=user_id.strip(),
                timestamp=timestamp.strip(),
                metadata=metadata,
            )
        )

    return actions


def _process_action(action: UserAction) -> Dict[str, Any]:
    logger.info(
        "Processing action_type=%s user_id=%s timestamp=%s",
        action.action_type,
        action.user_id,
        action.timestamp,
    )

    return {
        "user_id": action.user_id,
        "action_type": action.action_type,
        "timestamp": action.timestamp,
        "status": "processed",
        "metadata_keys": sorted(action.metadata.keys()),
    }


def _response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        headers = _normalize_headers(event.get("headers"))
        raw_body = _decode_body(event)
        _verify_signature(raw_body, headers)

        payload = _deserialize_payload(raw_body)
        actions = _deserialize_actions(payload)
        results = [_process_action(action) for action in actions]

        partner_id = payload.get("partner_id")
        return _response(
            200,
            {
                "ok": True,
                "partner_id": partner_id,
                "processed_count": len(results),
                "results": results,
            },
        )
    except BadRequestError as exc:
        logger.warning("Bad request: %s", exc)
        return _response(400, {"ok": False, "error": str(exc)})
    except UnauthorizedError as exc:
        logger.warning("Unauthorized request: %s", exc)
        return _response(401, {"ok": False, "error": str(exc)})
    except Exception:
        logger.exception("Unhandled error while processing webhook.")
        return _response(500, {"ok": False, "error": "Internal server error"})