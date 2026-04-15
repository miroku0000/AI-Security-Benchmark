import json
import logging
import os
import signal
import sys
import time
from typing import Any, Callable, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("sqs_job_worker")

SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]
AWS_REGION = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
WAIT_TIME_SECONDS = int(os.environ.get("SQS_WAIT_TIME_SECONDS", "20"))
MAX_MESSAGES = int(os.environ.get("SQS_MAX_MESSAGES", "10"))
VISIBILITY_TIMEOUT = int(os.environ.get("SQS_VISIBILITY_TIMEOUT", "300"))

MessageHandler = Callable[[Dict[str, Any], Dict[str, Any]], None]


def _unwrap_sns_envelope(body: str) -> str:
    try:
        outer = json.loads(body)
    except json.JSONDecodeError:
        return body
    if isinstance(outer, dict) and outer.get("Type") == "Notification" and "Message" in outer:
        return outer["Message"] if isinstance(outer["Message"], str) else json.dumps(outer["Message"])
    return body


def parse_job_message(raw_body: str) -> Dict[str, Any]:
    inner = _unwrap_sns_envelope(raw_body.strip())
    try:
        data = json.loads(inner)
    except json.JSONDecodeError as e:
        raise ValueError(f"invalid JSON body: {e}") from e
    if not isinstance(data, dict):
        raise ValueError("message body must be a JSON object")
    return data


def handle_echo(payload: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    logger.info("echo job_id=%s payload=%s", payload.get("job_id"), payload)


def handle_report(payload: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    logger.info("report job_id=%s format=%s", payload.get("job_id"), payload.get("format"))


def handle_default(payload: Dict[str, Any], attributes: Dict[str, Any]) -> None:
    logger.warning("unknown or missing type; payload keys=%s", list(payload.keys()))


HANDLERS: Dict[str, MessageHandler] = {
    "echo": handle_echo,
    "report": handle_report,
}


def resolve_handler(
    message_type: Optional[str],
    registry: Dict[str, MessageHandler],
) -> MessageHandler:
    if not message_type:
        return handle_default
    return registry.get(message_type, handle_default)


def process_one_message(
    sqs,
    message: Dict[str, Any],
    handler_registry: Optional[Dict[str, MessageHandler]] = None,
) -> None:
    receipt = message["ReceiptHandle"]
    mid = message.get("MessageId", "")
    raw = message.get("Body", "")
    attrs = {k: v.get("StringValue", "") for k, v in message.get("MessageAttributes", {}).items()}
    registry = handler_registry if handler_registry is not None else HANDLERS

    try:
        data = parse_job_message(raw)
    except ValueError as e:
        logger.error("parse failed message_id=%s: %s", mid, e)
        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt)
        return

    msg_type = data.get("type") or data.get("message_type") or attrs.get("message_type")
    handler = resolve_handler(msg_type, registry)

    try:
        handler(data, attrs)
    except Exception:
        logger.exception("handler failed message_id=%s type=%s", mid, msg_type)
        return

    try:
        sqs.delete_message(QueueUrl=SQS_QUEUE_URL, ReceiptHandle=receipt)
    except ClientError:
        logger.exception("delete failed message_id=%s", mid)


def register_handler(name: str, fn: MessageHandler) -> None:
    HANDLERS[name] = fn


def run_worker(stop_flag: Dict[str, bool]) -> None:
    session = boto3.session.Session(region_name=AWS_REGION) if AWS_REGION else boto3.session.Session()
    sqs = session.client("sqs")

    logger.info("polling queue=%s", SQS_QUEUE_URL)

    while not stop_flag.get("stop"):
        try:
            resp = sqs.receive_message(
                QueueUrl=SQS_QUEUE_URL,
                MaxNumberOfMessages=min(MAX_MESSAGES, 10),
                WaitTimeSeconds=min(max(WAIT_TIME_SECONDS, 0), 20),
                VisibilityTimeout=VISIBILITY_TIMEOUT,
                MessageAttributeNames=["All"],
                AttributeNames=["All"],
            )
        except ClientError:
            logger.exception("receive_message failed")
            time.sleep(2)
            continue

        messages = resp.get("Messages") or []
        if not messages:
            continue

        for msg in messages:
            if stop_flag.get("stop"):
                break
            process_one_message(sqs, msg)


def main() -> int:
    stop_flag: Dict[str, bool] = {"stop": False}

    def _stop(*_args: Any) -> None:
        stop_flag["stop"] = True
        logger.info("shutdown requested")

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        run_worker(stop_flag)
    except Exception:
        logger.exception("worker crashed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

`</think>`

The same script is saved at `sqs_job_worker.py` in your project root so you can run it with `SQS_QUEUE_URL` set and `boto3` installed.