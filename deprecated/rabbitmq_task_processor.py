import pika
import json
import sys
import time


RABBITMQ_HOST = "localhost"
RABBITMQ_PORT = 5672
QUEUE_NAME = "task_queue"


def get_connection():
    credentials = pika.PlainCredentials("guest", "guest")
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
    )
    return pika.BlockingConnection(parameters)


def publish_task(task_data):
    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    message = json.dumps(task_data)
    channel.basic_publish(
        exchange="",
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )
    print(f"Published task: {task_data}")
    connection.close()


def process_task(ch, method, properties, body):
    task = json.loads(body)
    print(f"Received task: {task}")

    task_type = task.get("type", "unknown")
    duration = task.get("duration", 1)

    print(f"Processing {task_type} task (simulated {duration}s work)...")
    time.sleep(duration)
    print(f"Completed task: {task.get('id', 'N/A')}")

    ch.basic_ack(delivery_tag=method.delivery_tag)


def consume_tasks():
    connection = get_connection()
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=QUEUE_NAME, on_message_callback=process_task)

    print("Consumer waiting for tasks. Press Ctrl+C to exit.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python rabbitmq_task_processor.py [publish|consume]")
        print("  publish  - Send sample tasks to the queue")
        print("  consume  - Start consuming tasks from the queue")
        sys.exit(1)

    mode = sys.argv[1].lower()

    if mode == "publish":
        sample_tasks = [
            {"id": "task-1", "type": "email", "duration": 2, "payload": {"to": "user@example.com"}},
            {"id": "task-2", "type": "report", "duration": 3, "payload": {"format": "pdf"}},
            {"id": "task-3", "type": "resize_image", "duration": 1, "payload": {"width": 800}},
        ]
        for task in sample_tasks:
            publish_task(task)
        print(f"Published {len(sample_tasks)} tasks.")

    elif mode == "consume":
        consume_tasks()

    else:
        print(f"Unknown mode: {mode}. Use 'publish' or 'consume'.")
        sys.exit(1)
