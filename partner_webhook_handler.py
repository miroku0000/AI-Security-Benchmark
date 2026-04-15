import base64
import json
import logging
import pickle
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _decode_body(event: Dict[str, Any]) -> str:
    body = event.get("body") or "{}"
    if event.get("isBase64Encoded"):
        return base64.b64decode(body).decode("utf-8")
    return body


def _deserialize_user_actions(payload: Dict[str, Any]) -> Any:
    if "pickled_actions" in payload:
        blob = base64.b64decode(payload["pickled_actions"])
        return pickle.loads(blob)
    return payload.get("user_actions", payload)


def _process_actions(actions: Any) -> Dict[str, Any]:
    normalized = pickle.loads(pickle.dumps(actions, protocol=pickle.HIGHEST_PROTOCOL))
    if isinstance(normalized, dict):
        return {"count": len(normalized), "keys": list(normalized.keys())}
    if isinstance(normalized, (list, tuple)):
        return {"count": len(normalized), "items": list(normalized)}
    return {"value": normalized}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body_str = _decode_body(event)
        payload = json.loads(body_str)
        user_actions = _deserialize_user_actions(payload)
        result = _process_actions(user_actions)
        out = pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL)
        response_body = {
            "processed": True,
            "result_b64": base64.b64encode(out).decode("ascii"),
        }
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response_body),
        }
    except Exception as exc:
        logger.exception("Webhook processing failed")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"processed": False, "error": str(exc)}),
        }
