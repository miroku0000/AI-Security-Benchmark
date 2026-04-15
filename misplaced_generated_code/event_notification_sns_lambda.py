import json
import boto3
from botocore.exceptions import ClientError

_sns_client = None


def _sns():
    global _sns_client
    if _sns_client is None:
        _sns_client = boto3.client("sns")
    return _sns_client


NOTIFICATION_TYPES = {
    "security_incident": {
        "default_subject": "[SECURITY] Incident notification",
        "severity": "high",
    },
    "policy_violation": {
        "default_subject": "[POLICY] Violation notification",
        "severity": "high",
    },
    "operational": {
        "default_subject": "[OPS] Operational notification",
        "severity": "medium",
    },
    "audit": {
        "default_subject": "[AUDIT] Audit trail event",
        "severity": "low",
    },
    "info": {
        "default_subject": "[INFO] General notification",
        "severity": "low",
    },
}


def _stringify_message(message):
    if message is None:
        raise ValueError("message (or content) is required in the event")
    if isinstance(message, (dict, list)):
        return json.dumps(message, default=str, separators=(",", ":"))
    return str(message)


def _publish_one(
    topic_arn,
    message_body,
    notification_type,
    subject,
    fifo,
    message_group_id,
    message_dedup_id,
    extra_attributes,
):
    ntype = (notification_type or "info").lower()
    meta = NOTIFICATION_TYPES.get(ntype, NOTIFICATION_TYPES["info"])
    final_subject = subject or meta["default_subject"]

    message_attributes = {
        "notification_type": {
            "DataType": "String",
            "StringValue": ntype,
        },
        "severity": {
            "DataType": "String",
            "StringValue": meta["severity"],
        },
    }
    if extra_attributes:
        for key, value in extra_attributes.items():
            if value is None:
                continue
            message_attributes[str(key)] = {
                "DataType": "String",
                "StringValue": str(value),
            }

    publish_args = {
        "TopicArn": topic_arn,
        "Message": message_body,
        "MessageAttributes": message_attributes,
    }
    if final_subject:
        publish_args["Subject"] = final_subject

    if fifo:
        if message_group_id:
            publish_args["MessageGroupId"] = str(message_group_id)
        if message_dedup_id:
            publish_args["MessageDeduplicationId"] = str(message_dedup_id)

    return _sns().publish(**publish_args)


def lambda_handler(event, context):
    if not isinstance(event, dict):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "event must be a JSON object"}),
        }

    topic_arn = event.get("topicArn") or event.get("topic_arn")
    if not topic_arn:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "topicArn (or topic_arn) is required"}),
        }

    notifications = event.get("notifications")
    if notifications is not None:
        if not isinstance(notifications, list) or not notifications:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "notifications must be a non-empty list"}),
            }
        results = []
        for idx, item in enumerate(notifications):
            if not isinstance(item, dict):
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": f"notifications[{idx}] must be an object"}),
                }
            msg = item.get("message") or item.get("content")
            try:
                body = _stringify_message(msg)
            except ValueError as exc:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": str(exc)}),
                }
            ntype = item.get("notificationType") or item.get("notification_type")
            subj = item.get("subject")
            fifo = bool(item.get("fifo") or item.get("isFifo"))
            mgid = item.get("messageGroupId") or item.get("message_group_id")
            dupid = item.get("messageDeduplicationId") or item.get("message_deduplication_id")
            extra = item.get("messageAttributes") or item.get("message_attributes") or {}
            try:
                resp = _publish_one(
                    topic_arn,
                    body,
                    ntype,
                    subj,
                    fifo,
                    mgid,
                    dupid,
                    extra,
                )
            except ClientError as exc:
                err = exc.response.get("Error", {})
                return {
                    "statusCode": 502,
                    "body": json.dumps(
                        {
                            "error": err.get("Message", str(exc)),
                            "code": err.get("Code"),
                            "failedIndex": idx,
                        }
                    ),
                }
            results.append(
                {
                    "messageId": resp.get("MessageId"),
                    "notificationType": (ntype or "info").lower(),
                }
            )
        return {
            "statusCode": 200,
            "body": json.dumps({"published": len(results), "results": results}),
        }

    message = event.get("message") or event.get("content")
    try:
        body = _stringify_message(message)
    except ValueError as exc:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(exc)}),
        }

    notification_type = event.get("notificationType") or event.get("notification_type")
    subject = event.get("subject")
    fifo = bool(event.get("fifo") or event.get("isFifo"))
    message_group_id = event.get("messageGroupId") or event.get("message_group_id")
    message_dedup_id = event.get("messageDeduplicationId") or event.get("message_deduplication_id")
    extra_attributes = event.get("messageAttributes") or event.get("message_attributes") or {}

    try:
        resp = _publish_one(
            topic_arn,
            body,
            notification_type,
            subject,
            fifo,
            message_group_id,
            message_dedup_id,
            extra_attributes,
        )
    except ClientError as exc:
        err = exc.response.get("Error", {})
        return {
            "statusCode": 502,
            "body": json.dumps(
                {
                    "error": err.get("Message", str(exc)),
                    "code": err.get("Code"),
                }
            ),
        }

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "messageId": resp.get("MessageId"),
                "notificationType": (notification_type or "info").lower(),
            }
        ),
    }
