import json
import logging
import signal
import sys
from kafka import KafkaConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BROKER = "localhost:9092"
TOPICS = ["financial-transactions"]
GROUP_ID = "transaction-processor"

running = True


def handle_shutdown(signum, frame):
    global running
    logger.info("Shutting down consumer...")
    running = False


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


# --- Transaction handlers ---

def handle_deposit(tx):
    account = tx["account_id"]
    amount = tx["amount"]
    logger.info(f"DEPOSIT: {amount} into account {account}")
    # TODO: integrate with account service
    return {"status": "processed", "account_id": account, "amount": amount}


def handle_withdrawal(tx):
    account = tx["account_id"]
    amount = tx["amount"]
    if amount <= 0:
        logger.warning(f"Invalid withdrawal amount: {amount}")
        return {"status": "rejected", "reason": "invalid_amount"}
    logger.info(f"WITHDRAWAL: {amount} from account {account}")
    return {"status": "processed", "account_id": account, "amount": amount}


def handle_transfer(tx):
    src = tx["source_account"]
    dst = tx["destination_account"]
    amount = tx["amount"]
    if amount <= 0:
        logger.warning(f"Invalid transfer amount: {amount}")
        return {"status": "rejected", "reason": "invalid_amount"}
    logger.info(f"TRANSFER: {amount} from {src} to {dst}")
    return {"status": "processed", "source": src, "destination": dst, "amount": amount}


def handle_refund(tx):
    account = tx["account_id"]
    amount = tx["amount"]
    ref = tx.get("original_transaction_id", "unknown")
    logger.info(f"REFUND: {amount} to account {account} (ref: {ref})")
    return {"status": "processed", "account_id": account, "amount": amount}


# Explicit handler registry — only known transaction types are accepted.
HANDLERS = {
    "deposit": handle_deposit,
    "withdrawal": handle_withdrawal,
    "transfer": handle_transfer,
    "refund": handle_refund,
}


def validate_message(msg):
    if not isinstance(msg, dict):
        return False, "message is not a dict"
    if "transaction_type" not in msg:
        return False, "missing transaction_type"
    if msg["transaction_type"] not in HANDLERS:
        return False, f"unknown transaction_type: {msg['transaction_type']}"
    return True, None


def process_message(raw_value):
    try:
        msg = json.loads(raw_value)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to deserialize message: {e}")
        return

    valid, reason = validate_message(msg)
    if not valid:
        logger.warning(f"Invalid message dropped: {reason}")
        return

    tx_type = msg["transaction_type"]
    handler = HANDLERS[tx_type]
    try:
        result = handler(msg)
        logger.info(f"Result: {result}")
    except KeyError as e:
        logger.error(f"Missing required field in {tx_type} transaction: {e}")
    except Exception:
        logger.exception(f"Error processing {tx_type} transaction")


def main():
    logger.info(f"Connecting to Kafka broker at {BROKER}, topics={TOPICS}")
    consumer = KafkaConsumer(
        *TOPICS,
        bootstrap_servers=BROKER,
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=None,  # we handle deserialization ourselves
    )
    logger.info("Consumer started. Waiting for messages...")

    try:
        while running:
            records = consumer.poll(timeout_ms=1000)
            for topic_partition, messages in records.items():
                for message in messages:
                    logger.info(
                        f"Received: topic={message.topic} partition={message.partition} offset={message.offset}"
                    )
                    process_message(message.value)
    finally:
        consumer.close()
        logger.info("Consumer closed.")


if __name__ == "__main__":
    main()