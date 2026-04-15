import hashlib
import json
import logging
import os
import re
import uuid
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
if not logger.handlers:
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

_TABLE = os.environ["TABLE_NAME"]
_SECRET_ARN = os.environ["SECRET_ARN"]

_ddb = boto3.resource("dynamodb")
_sm = boto3.client("secretsmanager")
_table = _ddb.Table(_TABLE)

_PAYMENT_ID_RE = re.compile(r"^[a-zA-Z0-9._:-]{8,128}$")


def _mask_id(payment_id: str) -> str:
    digest = hashlib.sha256(payment_id.encode("utf-8")).hexdigest()[:12]
    return f"payment_id_sha256:{digest}"


def _validate_payload(body: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    payment_id = str(body.get("payment_id", "")).strip()
    if not _PAYMENT_ID_RE.match(payment_id):
        raise ValueError("invalid payment_id")
    amount = body.get("amount")
    if amount is None:
        raise ValueError("amount required")
    if isinstance(amount, bool):
        raise ValueError("invalid amount type")
    try:
        dec = Decimal(str(amount))
    except Exception as exc:
        raise ValueError("invalid amount") from exc
    if dec <= 0 or dec.as_tuple().exponent < -2:
        raise ValueError("amount must be positive with at most 2 decimal places")
    currency = str(body.get("currency", "USD")).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValueError("invalid currency")
    metadata_raw = body.get("metadata") or {}
    if not isinstance(metadata_raw, dict):
        raise ValueError("metadata must be an object")
    metadata = {str(k)[:64]: str(v)[:256] for k, v in list(metadata_raw.items())[:32]}
    return payment_id, {"amount": dec, "currency": currency, "metadata": metadata}


def _load_processor_secret() -> dict[str, Any]:
    try:
        resp = _sm.get_secret_value(SecretId=_SECRET_ARN)
    except ClientError:
        logger.exception("failed to read secret", extra={"secret_arn": _SECRET_ARN})
        raise
    return json.loads(resp["SecretString"])


def _process_payment(
    payment_id: str, payload: dict[str, Any], idempotency_key: str | None
) -> dict[str, Any]:
    _load_processor_secret()
    now = str(uuid.uuid4())
    item = {
        "payment_id": payment_id,
        "amount": payload["amount"],
        "currency": payload["currency"],
        "status": "PROCESSED",
        "request_token": now,
        "metadata": payload["metadata"],
    }
    if idempotency_key:
        item["idempotency_key"] = idempotency_key[:128]
    try:
        kwargs: dict[str, Any] = {
            "Item": item,
            "ConditionExpression": "attribute_not_exists(payment_id)",
        }
        if idempotency_key:
            kwargs["ConditionExpression"] = (
                "attribute_not_exists(payment_id) AND attribute_not_exists(idempotency_key)"
            )
        _table.put_item(**kwargs)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            existing = _table.get_item(Key={"payment_id": payment_id}, ConsistentRead=True).get(
                "Item"
            )
            if existing:
                logger.info(
                    "idempotent replay",
                    extra={"masked_id": _mask_id(payment_id)},
                )
                return {
                    "ok": True,
                    "payment_id": payment_id,
                    "status": existing.get("status", "UNKNOWN"),
                    "duplicate": True,
                }
        logger.exception(
            "dynamo write failed",
            extra={"masked_id": _mask_id(payment_id)},
        )
        raise
    logger.info("payment recorded", extra={"masked_id": _mask_id(payment_id)})
    return {"ok": True, "payment_id": payment_id, "status": "PROCESSED", "duplicate": False}


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    try:
        if "body" in event and event["body"] is not None:
            raw = event["body"]
            body = json.loads(raw) if isinstance(raw, str) else raw
        else:
            body = event
        idem = None
        if isinstance(event.get("headers"), dict):
            idem = event["headers"].get("x-idempotency-key") or event["headers"].get(
                "X-Idempotency-Key"
            )
        payment_id, payload = _validate_payload(body)
        result = _process_payment(payment_id, payload, idem)
        return {"statusCode": 200, "headers": headers, "body": json.dumps(result)}
    except ValueError as ve:
        logger.warning("validation error: %s", str(ve))
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({"ok": False, "error": "invalid_request"}),
        }
    except Exception:
        logger.exception("unhandled error in payment handler")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({"ok": False, "error": "internal_error"}),
        }
