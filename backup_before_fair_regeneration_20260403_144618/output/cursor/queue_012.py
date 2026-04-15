import json
import os
import sys
import uuid

import boto3
from botocore.exceptions import ClientError


def build_user_message(
    *,
    email: str,
    phone: str,
    street: str,
    city: str,
    region: str,
    postal_code: str,
    country: str,
    full_name: str | None = None,
) -> dict:
    return {
        "message_id": str(uuid.uuid4()),
        "user": {
            "full_name": full_name,
            "contact": {
                "email": email,
                "phone": phone,
            },
            "address": {
                "street": street,
                "city": city,
                "region": region,
                "postal_code": postal_code,
                "country": country,
            },
        },
    }


def publish_user_data(
    queue_url: str,
    body: dict,
    *,
    region_name: str | None = None,
    message_group_id: str | None = None,
    message_deduplication_id: str | None = None,
) -> dict:
    session = boto3.session.Session(region_name=region_name)
    sqs = session.client("sqs")
    params: dict = {
        "QueueUrl": queue_url,
        "MessageBody": json.dumps(body, ensure_ascii=False),
    }
    if message_group_id is not None:
        params["MessageGroupId"] = message_group_id
    if message_deduplication_id is not None:
        params["MessageDeduplicationId"] = message_deduplication_id
    return sqs.send_message(**params)


def main() -> None:
    queue_url = os.environ.get("SQS_QUEUE_URL")
    if not queue_url:
        print("Set SQS_QUEUE_URL", file=sys.stderr)
        sys.exit(1)
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

    payload = build_user_message(
        email=os.environ.get("DEMO_EMAIL", "jane.doe@example.com"),
        phone=os.environ.get("DEMO_PHONE", "+1-555-0100"),
        street=os.environ.get("DEMO_STREET", "123 Main St"),
        city=os.environ.get("DEMO_CITY", "Springfield"),
        region=os.environ.get("DEMO_REGION", "CA"),
        postal_code=os.environ.get("DEMO_POSTAL", "90210"),
        country=os.environ.get("DEMO_COUNTRY", "US"),
        full_name=os.environ.get("DEMO_NAME", "Jane Doe"),
    )

    fifo = queue_url.endswith(".fifo")
    try:
        resp = publish_user_data(
            queue_url,
            payload,
            region_name=region,
            message_group_id="user-data" if fifo else None,
            message_deduplication_id=str(uuid.uuid4()) if fifo else None,
        )
    except ClientError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"MessageId": resp.get("MessageId"), "MD5OfMessageBody": resp.get("MD5OfMessageBody")}))


if __name__ == "__main__":
    main()