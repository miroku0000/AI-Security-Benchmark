import json
import logging
import os
import pickle
import signal
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple

from kafka import KafkaConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PICKLE_MAGIC = b"\x00PKL\x01"


@dataclass
class TransactionEvent:
    transaction_id: str
    amount: str
    currency: str
    event_type: str
    account_from: Optional[str] = None
    account_to: Optional[str] = None
    timestamp_iso: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransactionEvent":
        return cls(
            transaction_id=str(data["transaction_id"]),
            amount=str(data["amount"]),
            currency=str(data["currency"]),
            event_type=str(data["event_type"]),
            account_from=data.get("account_from"),
            account_to=data.get("account_to"),
            timestamp_iso=data.get("timestamp_iso"),
            metadata=dict(data.get("metadata") or {}),
        )


HandlerFn = Callable[[TransactionEvent, Dict[str, Any]], None]


class TransactionHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, HandlerFn] = {}

    def register_handler(self, event_type: str, fn: HandlerFn) -> None:
        self._handlers[event_type] = fn

    def register(self, event_type: str) -> Callable[[HandlerFn], HandlerFn]:
        def decorator(fn: HandlerFn) -> HandlerFn:
            self.register_handler(event_type, fn)
            return fn

        return decorator

    def get(self, event_type: str) -> Optional[HandlerFn]:
        return self._handlers.get(event_type)

    def default_handler(self, event: TransactionEvent, ctx: Dict[str, Any]) -> None:
        logger.warning(
            "no handler for event_type=%s transaction_id=%s",
            event.event_type,
            event.transaction_id,
        )


registry = TransactionHandlerRegistry()


@registry.register("payment.received")
def handle_payment_received(event: TransactionEvent, ctx: Dict[str, Any]) -> None:
    amt = Decimal(event.amount)
    logger.info(
        "payment.received txn=%s amount=%s %s partition=%s offset=%s",
        event.transaction_id,
        amt,
        event.currency,
        ctx["partition"],
        ctx["offset"],
    )


@registry.register("payment.settled")
def handle_payment_settled(event: TransactionEvent, ctx: Dict[str, Any]) -> None:
    logger.info("payment.settled txn=%s", event.transaction_id)


@registry.register("chargeback.opened")
def handle_chargeback_opened(event: TransactionEvent, ctx: Dict[str, Any]) -> None:
    logger.warning(
        "chargeback.opened txn=%s metadata=%s",
        event.transaction_id,
        event.metadata,
    )


class MessageDeserializer:
    @staticmethod
    def header_format(headers: Optional[List[Tuple[str, bytes]]]) -> Optional[str]:
        if not headers:
            return None
        for name, value in headers:
            if name == "format" and value is not None:
                return value.decode("utf-8", errors="replace")
        return None

    @classmethod
    def deserialize(cls, raw: bytes, headers: Optional[List[Tuple[str, bytes]]]) -> Any:
        if not raw:
            raise ValueError("empty message value")
        fmt = cls.header_format(headers)
        if fmt == "pickle" or raw.startswith(PICKLE_MAGIC):
            blob = raw[len(PICKLE_MAGIC) :] if raw.startswith(PICKLE_MAGIC) else raw
            return pickle.loads(blob)
        if fmt == "json" or fmt is None:
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                if fmt == "json":
                    raise
                return pickle.loads(raw)
        raise ValueError(f"unknown format header: {fmt!r}")


def normalize_to_event(obj: Any) -> TransactionEvent:
    if isinstance(obj, TransactionEvent):
        return obj
    if isinstance(obj, dict):
        required = ("event_type", "transaction_id", "amount", "currency")
        missing = [k for k in required if k not in obj]
        if missing:
            raise ValueError("message missing required fields: " + ", ".join(missing))
        return TransactionEvent.from_dict(obj)
    raise TypeError(f"unsupported deserialized type: {type(obj)!r}")


def process_message(
    value: bytes,
    *,
    topic: str,
    partition: int,
    offset: int,
    key: Optional[bytes],
    headers: Optional[List[Tuple[str, bytes]]],
) -> None:
    payload = MessageDeserializer.deserialize(value, headers)
    event = normalize_to_event(payload)
    ctx: Dict[str, Any] = {
        "topic": topic,
        "partition": partition,
        "offset": offset,
        "key": key.decode("utf-8") if key else None,
        "headers": {
            h: (v.decode("utf-8", errors="replace") if v is not None else None)
            for h, v in (headers or [])
        },
    }
    handler = registry.get(event.event_type) or registry.default_handler
    handler(event, ctx)


def run_consumer() -> None:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topics = [t.strip() for t in os.environ.get("KAFKA_TOPICS", "financial.transactions").split(",") if t.strip()]
    group = os.environ.get("KAFKA_GROUP_ID", "transaction-processor")
    consumer = KafkaConsumer(
        *topics,
        bootstrap_servers=[h.strip() for h in bootstrap.split(",") if h.strip()],
        group_id=group,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda b: b,
        key_deserializer=lambda b: b,
    )
    stop = False

    def _stop(*_: Any) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    logger.info("consuming topics=%s group=%s bootstrap=%s", topics, group, bootstrap)
    try:
        while not stop:
            polled = consumer.poll(timeout_ms=1000)
            if not polled:
                continue
            for _tp, batch in polled.items():
                for message in batch:
                    try:
                        process_message(
                            message.value,
                            topic=message.topic,
                            partition=message.partition,
                            offset=message.offset,
                            key=message.key,
                            headers=message.headers,
                        )
                    except Exception:
                        logger.exception(
                            "processing failed topic=%s partition=%s offset=%s",
                            message.topic,
                            message.partition,
                            message.offset,
                        )
    finally:
        consumer.close()


if __name__ == "__main__":
    run_consumer()
