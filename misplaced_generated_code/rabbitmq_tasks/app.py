import argparse
import json
import sys
import uuid

import pika

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
QUEUE_NAME = "distributed_tasks"


def connect():
    params = pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
    return pika.BlockingConnection(params)


def publish(count: int) -> None:
    connection = connect()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        for i in range(count):
            task = {
                "task_id": str(uuid.uuid4()),
                "kind": "process",
                "data": {"sequence": i},
            }
            body = json.dumps(task).encode("utf-8")
            channel.basic_publish(
                exchange="",
                routing_key=QUEUE_NAME,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=2,
                ),
            )
    finally:
        connection.close()


def consume() -> None:
    connection = connect()
    try:
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)

        def on_message(ch, method, properties, body):
            try:
                payload = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                payload = {"error": "invalid_json", "raw": body.decode("utf-8", errors="replace")}
            print(json.dumps({"status": "processed", "task": payload}))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=on_message)
        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RabbitMQ task publisher and consumer")
    sub = parser.add_subparsers(dest="command", required=True)

    pub = sub.add_parser("publish", help="Send task messages to the queue")
    pub.add_argument(
        "-n",
        "--count",
        type=int,
        default=1,
        help="Number of tasks to enqueue",
    )

    sub.add_parser("consume", help="Process tasks from the queue")

    args = parser.parse_args(argv)
    if args.command == "publish":
        if args.count < 1:
            print("count must be >= 1", file=sys.stderr)
            return 2
        publish(args.count)
        return 0
    consume()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
