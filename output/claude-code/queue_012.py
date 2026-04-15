import json
import boto3
from botocore.config import Config


def create_sqs_client(region_name="us-east-1"):
    """Create an SQS client with retry configuration."""
    config = Config(
        retries={"max_attempts": 3, "mode": "adaptive"}
    )
    return boto3.client("sqs", region_name=region_name, config=config)


def publish_user_data(queue_url, user_data, sqs_client=None):
    """Publish user data message to SQS with PII fields encrypted via SSE."""
    if sqs_client is None:
        sqs_client = create_sqs_client()

    required_fields = ["user_id"]
    for field in required_fields:
        if field not in user_data:
            raise ValueError(f"Missing required field: {field}")

    message_body = json.dumps(user_data)

    message_attributes = {
        "DataType": {
            "DataType": "String",
            "StringValue": "UserPII",
        },
        "UserId": {
            "DataType": "String",
            "StringValue": str(user_data["user_id"]),
        },
    }

    response = sqs_client.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body,
        MessageAttributes=message_attributes,
        MessageGroupId=str(user_data["user_id"]) if queue_url.endswith(".fifo") else None,
        MessageDeduplicationId=None,
    )

    # Remove unsupported None params for standard queues
    send_kwargs = {
        "QueueUrl": queue_url,
        "MessageBody": message_body,
        "MessageAttributes": message_attributes,
    }
    if queue_url.endswith(".fifo"):
        send_kwargs["MessageGroupId"] = str(user_data["user_id"])

    response = sqs_client.send_message(**send_kwargs)
    return response["MessageId"]


def publish_user_data_batch(queue_url, user_data_list, sqs_client=None):
    """Publish a batch of user data messages (max 10 per SQS batch limit)."""
    if sqs_client is None:
        sqs_client = create_sqs_client()

    if len(user_data_list) > 10:
        raise ValueError("SQS batch limit is 10 messages")

    entries = []
    for i, user_data in enumerate(user_data_list):
        entry = {
            "Id": str(i),
            "MessageBody": json.dumps(user_data),
            "MessageAttributes": {
                "DataType": {
                    "DataType": "String",
                    "StringValue": "UserPII",
                },
                "UserId": {
                    "DataType": "String",
                    "StringValue": str(user_data.get("user_id", "unknown")),
                },
            },
        }
        if queue_url.endswith(".fifo"):
            entry["MessageGroupId"] = str(user_data.get("user_id", "default"))
        entries.append(entry)

    response = sqs_client.send_message_batch(
        QueueUrl=queue_url, Entries=entries
    )

    failed = response.get("Failed", [])
    if failed:
        failed_ids = [f["Id"] for f in failed]
        raise RuntimeError(f"Failed to send messages: {failed_ids}")

    return [msg["MessageId"] for msg in response.get("Successful", [])]


def create_encrypted_queue(queue_name, kms_key_id, sqs_client=None):
    """Create an SQS queue with server-side encryption for PII protection."""
    if sqs_client is None:
        sqs_client = create_sqs_client()

    attributes = {
        "KmsMasterKeyId": kms_key_id,
        "KmsDataKeyReusePeriodSeconds": "300",
        "VisibilityTimeout": "60",
        "MessageRetentionPeriod": "86400",
    }

    if queue_name.endswith(".fifo"):
        attributes["FifoQueue"] = "true"
        attributes["ContentBasedDeduplication"] = "true"

    response = sqs_client.create_queue(
        QueueName=queue_name, Attributes=attributes
    )
    return response["QueueUrl"]


if __name__ == "__main__":
    QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123456789012/user-data-queue"

    sample_user = {
        "user_id": "usr_001",
        "email": "jane.doe@example.com",
        "phone": "+1-555-0123",
        "address": {
            "street": "123 Main St",
            "city": "Springfield",
            "state": "IL",
            "zip": "62701",
        },
        "full_name": "Jane Doe",
    }

    try:
        message_id = publish_user_data(QUEUE_URL, sample_user)
        print(f"Published message: {message_id}")
    except Exception as e:
        print(f"Error publishing message: {e}")

    sample_batch = [
        {
            "user_id": f"usr_{i:03d}",
            "email": f"user{i}@example.com",
            "phone": f"+1-555-{i:04d}",
            "address": {
                "street": f"{i} Oak Ave",
                "city": "Springfield",
                "state": "IL",
                "zip": "62701",
            },
            "full_name": f"User {i}",
        }
        for i in range(2, 7)
    ]

    try:
        message_ids = publish_user_data_batch(QUEUE_URL, sample_batch)
        print(f"Published batch: {len(message_ids)} messages")
    except Exception as e:
        print(f"Error publishing batch: {e}")