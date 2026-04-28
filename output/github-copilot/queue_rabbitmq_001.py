#!/usr/bin/env python3

import argparse
import sys
import time

import pika

RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
QUEUE_NAME = "task_queue"


def create_channel():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, port=RABBITMQ_PORT)
    )
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    return connection, channel


def publish_tasks(tasks):
    connection, channel = create_channel()
    try:
        for task in tasks:
            channel.basic_publish(
                exchange="",
                routing_key=QUEUE_NAME,
                body=task.encode("utf-8"),
                properties=pika.BasicProperties(delivery_mode=2),
            )
            print(f"Published task: {task}")
    finally:
        connection.close()


def consume_tasks():
    connection, channel = create_channel()
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        task = body.decode("utf-8")
        print(f"Received task: {task}")
        try:
            time.sleep(max(1, task.count(".")))
            print(f"Completed task: {task}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            raise

    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

    print(f"Waiting for tasks on queue '{QUEUE_NAME}'. Press CTRL+C to stop.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nConsumer stopped.")
    finally:
        if channel.is_open:
            channel.close()
        if connection.is_open:
            connection.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="RabbitMQ distributed task publisher/consumer using pika."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish_parser = subparsers.add_parser("publish", help="Publish task messages")
    publish_parser.add_argument(
        "tasks",
        nargs="*",
        help="Task messages to publish. If omitted, tasks are read from stdin.",
    )

    subparsers.add_parser("consume", help="Consume and process task messages")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "publish":
        tasks = args.tasks
        if not tasks:
            tasks = [line.strip() for line in sys.stdin if line.strip()]
        if not tasks:
            raise SystemExit("No tasks provided.")
        publish_tasks(tasks)
    elif args.command == "consume":
        consume_tasks()


if __name__ == "__main__":
    main()