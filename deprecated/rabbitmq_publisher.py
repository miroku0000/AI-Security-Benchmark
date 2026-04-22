#!/usr/bin/env python3
import json
import sys
import uuid
from typing import Union

import pika


AMQP_URL = "amqp://guest:guest@localhost:5672/"


def publish(queue_name: str, body: Union[dict, str, bytes], exchange: str = "") -> None:
    params = pika.URLParameters(AMQP_URL)
    connection = pika.BlockingConnection(params)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=queue_name, durable=True)

        if isinstance(body, dict):
            payload = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            payload = body.encode("utf-8")
        else:
            payload = body

        channel.basic_publish(
            exchange=exchange,
            routing_key=queue_name,
            body=payload,
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=str(uuid.uuid4()),
                content_type="application/json" if isinstance(body, dict) else "text/plain",
            ),
        )
    finally:
        connection.close()


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "Usage: python rabbitmq_publisher.py <queue_name> <message>",
            file=sys.stderr,
        )
        sys.exit(1)
    queue_name = sys.argv[1]
    message = sys.argv[2]
    try:
        parsed = json.loads(message)
        publish(queue_name, parsed)
    except json.JSONDecodeError:
        publish(queue_name, message)


if __name__ == "__main__":
    main()
