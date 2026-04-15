import json
import logging
import signal
import sys
import time

import boto3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

_running = True


def handle_shutdown(signum, frame):
    global _running
    logger.info("Shutdown signal received, finishing current batch...")
    _running = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


# --- Message handlers ---

def handle_send_email(payload):
    to = payload["to"]
    subject = payload["subject"]
    logger.info("Sending email to %s: %s", to, subject)


def handle_process_image(payload):
    image_url = payload["image_url"]
    operations = payload.get("operations", [])
    logger.info("Processing image %s with operations %s", image_url, operations)


def handle_generate_report(payload):
    report_type = payload["report_type"]
    params = payload.get("params", {})
    logger.info("Generating %s report with params %s", report_type, params)


def handle_cleanup(payload):
    target = payload["target"]
    older_than_days = payload.get("older_than_days", 30)
    logger.info("Cleaning up %s older than %d days", target, older_than_days)


MESSAGE_HANDLERS = {
    "send_email": handle_send_email,
    "process_image": handle_process_image,
    "generate_report": handle_generate_report,
    "cleanup": handle_cleanup,
}


def register_handler(message_type, handler_fn):
    MESSAGE_HANDLERS[message_type] = handler_fn


def process_message(message):
    body = json.loads(message.body)
    message_type = body.get("type")
    payload = body.get("payload", {})

    if not message_type:
        logger.error("Message missing 'type' field: %s", message.message_id)
        return False

    handler = MESSAGE_HANDLERS.get(message_type)
    if handler is None:
        logger.error("No handler registered for message type: %s", message_type)
        return False

    handler(payload)
    return True


def poll(queue_url, region_name="us-east-1", max_messages=10, wait_time=20, visibility_timeout=60):
    sqs = boto3.resource("sqs", region_name=region_name)
    queue = sqs.Queue(queue_url)

    logger.info("Starting SQS worker on queue: %s", queue_url)
    logger.info("Registered handlers: %s", list(MESSAGE_HANDLERS.keys()))

    while _running:
        messages = queue.receive_messages(
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=visibility_timeout,
            AttributeNames=["All"],
        )

        for message in messages:
            try:
                success = process_message(message)
                if success:
                    message.delete()
                    logger.info("Processed and deleted message %s", message.message_id)
                else:
                    logger.warning("Message %s was not processed successfully; leaving on queue", message.message_id)
            except json.JSONDecodeError:
                logger.exception("Invalid JSON in message %s", message.message_id)
                message.delete()
            except Exception:
                logger.exception("Failed to process message %s", message.message_id)

        if not messages:
            time.sleep(1)

    logger.info("Worker stopped.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <queue-url> [region]")
        sys.exit(1)

    url = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else "us-east-1"
    poll(url, region_name=region)