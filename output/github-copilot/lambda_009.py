import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Mapping, Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

# Shared IAM role definition for Lambda functions that need the same bounded access.
# Attach this single role to each microservice Lambda that uses these integrations, and
# remove any statement a given function does not need.
#
# {
#   "RoleName": "MicroserviceSharedLambdaRole",
#   "AssumeRolePolicyDocument": {
#     "Version": "2012-10-17",
#     "Statement": [
#       {
#         "Effect": "Allow",
#         "Principal": { "Service": "lambda.amazonaws.com" },
#         "Action": ["sts:AssumeRole"]
#       }
#     ]
#   },
#   "Policies": [
#     {
#       "PolicyName": "MicroserviceSharedAccess",
#       "PolicyDocument": {
#         "Version": "2012-10-17",
#         "Statement": [
#           {
#             "Sid": "WriteFunctionLogs",
#             "Effect": "Allow",
#             "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
#             "Resource": [
#               "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/microservice-*:*"
#             ]
#           },
#           {
#             "Sid": "AccessArtifactsBucketObjects",
#             "Effect": "Allow",
#             "Action": ["s3:GetObject", "s3:PutObject"],
#             "Resource": [
#               "arn:aws:s3:::${ARTIFACT_BUCKET}/microservice-input/*",
#               "arn:aws:s3:::${ARTIFACT_BUCKET}/microservice-output/*"
#             ]
#           },
#           {
#             "Sid": "ListArtifactsBucketPrefixes",
#             "Effect": "Allow",
#             "Action": ["s3:ListBucket"],
#             "Resource": ["arn:aws:s3:::${ARTIFACT_BUCKET}"],
#             "Condition": {
#               "StringLike": {
#                 "s3:prefix": ["microservice-input/*", "microservice-output/*"]
#               }
#             }
#           },
#           {
#             "Sid": "WriteMetadataTable",
#             "Effect": "Allow",
#             "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem"],
#             "Resource": [
#               "arn:aws:dynamodb:${AWS_REGION}:${AWS_ACCOUNT_ID}:table/${METADATA_TABLE}"
#             ]
#           },
#           {
#             "Sid": "PublishNotifications",
#             "Effect": "Allow",
#             "Action": ["sns:Publish"],
#             "Resource": [
#               "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:${NOTIFICATIONS_TOPIC_NAME}"
#             ]
#           },
#           {
#             "Sid": "QueueJobs",
#             "Effect": "Allow",
#             "Action": ["sqs:SendMessage", "sqs:GetQueueAttributes"],
#             "Resource": [
#               "arn:aws:sqs:${AWS_REGION}:${AWS_ACCOUNT_ID}:${JOBS_QUEUE_NAME}"
#             ]
#           }
#         ]
#       }
#     }
#   ]
# }

ACTION_CREATE_UPLOAD_URL = "create_upload_url"
ACTION_STORE_METADATA = "store_metadata"
ACTION_PUBLISH_NOTIFICATION = "publish_notification"
ACTION_ENQUEUE_JOB = "enqueue_job"

ALLOWED_ACTIONS = {
    ACTION_CREATE_UPLOAD_URL,
    ACTION_STORE_METADATA,
    ACTION_PUBLISH_NOTIFICATION,
    ACTION_ENQUEUE_JOB,
}
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/pdf",
    "application/octet-stream",
    "text/csv",
    "text/plain",
}
SERVICE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
OBJECT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
ORIGIN_PATTERN = re.compile(r"^https://[A-Za-z0-9.-]+(:[0-9]{1,5})?$")

_s3_client = None
_dynamodb_resource = None
_sns_client = None
_sqs_client = None


class ValidationError(ValueError):
    pass


def lambda_handler(event: Any, context: Any) -> Dict[str, Any]:
    headers = build_headers()

    try:
        request = parse_request(event, context)

        if request["action"] == ACTION_CREATE_UPLOAD_URL:
            result = create_upload_url(request)
            status_code = 200
        elif request["action"] == ACTION_STORE_METADATA:
            result = store_metadata(request)
            status_code = 201
        elif request["action"] == ACTION_PUBLISH_NOTIFICATION:
            result = publish_notification(request)
            status_code = 202
        else:
            result = enqueue_job(request)
            status_code = 202

        return response(status_code, {"status": "ok", "result": result}, headers)
    except ValidationError as exc:
        return response(400, {"message": str(exc)}, headers)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "unknown")
        if error_code == "ConditionalCheckFailedException":
            return response(409, {"message": "metadata item already exists"}, headers)
        return response(502, {"message": "AWS service request failed", "error_code": error_code}, headers)


def parse_request(event: Any, context: Any) -> Dict[str, Any]:
    if not isinstance(event, dict):
        raise ValidationError("event must be a JSON object")

    is_base64_encoded = event.get("isBase64Encoded") if isinstance(event, dict) else False
    if is_base64_encoded is True:
        raise ValidationError("base64-encoded bodies are not supported")

    body = event.get("body") if isinstance(event, dict) else None
    if body is None:
        document = event
    else:
        if not isinstance(body, str) or not body.strip():
            raise ValidationError("body must be a non-empty JSON string")
        if len(body.encode("utf-8")) > 32768:
            raise ValidationError("body must be 32 KB or smaller")
        try:
            document = json.loads(body, parse_float=Decimal)
        except json.JSONDecodeError as exc:
            raise ValidationError("body must be valid JSON") from exc

    if not isinstance(document, dict):
        raise ValidationError("request payload must be a JSON object")

    action = document.get("action")
    service = document.get("service")
    payload = document.get("payload")
    correlation_id = document.get("correlation_id")

    request_context = event.get("requestContext") if isinstance(event, dict) else None
    request_id = request_context.get("requestId") if isinstance(request_context, dict) else None
    fallback_request_id = getattr(context, "aws_request_id", None)

    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
        raise ValidationError("action is invalid")
    if not isinstance(service, str) or not SERVICE_PATTERN.fullmatch(service):
        raise ValidationError("service must match ^[a-z0-9][a-z0-9-]{1,62}$")
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a JSON object")

    normalized_correlation_id = correlation_id
    if not isinstance(normalized_correlation_id, str):
        normalized_correlation_id = request_id or fallback_request_id or str(uuid4())

    if not IDENTIFIER_PATTERN.fullmatch(normalized_correlation_id):
        raise ValidationError("correlation_id contains unsupported characters")

    ensure_json_value(payload, depth=0)

    return {
        "action": action,
        "service": service,
        "payload": payload,
        "correlation_id": normalized_correlation_id,
    }


def ensure_json_value(value: Any, depth: int) -> None:
    if depth > 5:
        raise ValidationError("payload nesting exceeds the supported depth")

    if value is None or isinstance(value, (str, bool, int, Decimal)):
        return

    if isinstance(value, list):
        if len(value) > 50:
            raise ValidationError("payload lists may not contain more than 50 items")
        for item in value:
            ensure_json_value(item, depth + 1)
        return

    if isinstance(value, dict):
        if len(value) > 50:
            raise ValidationError("payload objects may not contain more than 50 keys")
        for key, item in value.items():
            if not isinstance(key, str) or not IDENTIFIER_PATTERN.fullmatch(key):
                raise ValidationError("payload keys contain unsupported characters")
            ensure_json_value(item, depth + 1)
        return

    raise ValidationError("payload contains unsupported value types")


def create_upload_url(request: Mapping[str, Any]) -> Dict[str, Any]:
    payload = request["payload"]
    object_name = payload.get("object_name")
    content_type = payload.get("content_type")

    if not isinstance(object_name, str) or not OBJECT_NAME_PATTERN.fullmatch(object_name):
        raise ValidationError("payload.object_name is invalid")
    if object_name.startswith("/") or ".." in object_name:
        raise ValidationError("payload.object_name must stay within the service prefix")
    if not isinstance(content_type, str) or content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError("payload.content_type is invalid")

    bucket_name = require_env("ARTIFACT_BUCKET")
    expires_in = 300
    object_key = (
        f"microservice-input/{request['service']}/"
        f"{request['correlation_id']}/{object_name}"
    )

    upload_url = s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": bucket_name,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=expires_in,
        HttpMethod="PUT",
    )

    return {
        "operation": ACTION_CREATE_UPLOAD_URL,
        "bucket": bucket_name,
        "key": object_key,
        "content_type": content_type,
        "expires_in_seconds": expires_in,
        "upload_url": upload_url,
    }


def store_metadata(request: Mapping[str, Any]) -> Dict[str, Any]:
    payload = request["payload"]
    item_id = payload.get("item_id")
    attributes = payload.get("attributes")

    if not isinstance(item_id, str) or not IDENTIFIER_PATTERN.fullmatch(item_id):
        raise ValidationError("payload.item_id is invalid")
    if not isinstance(attributes, dict):
        raise ValidationError("payload.attributes must be an object")

    ensure_json_value(attributes, depth=0)

    table_name = require_env("METADATA_TABLE")
    item = {
        "pk": f"SERVICE#{request['service']}",
        "sk": f"ITEM#{item_id}",
        "correlation_id": request["correlation_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "attributes": attributes,
    }

    dynamodb_resource().Table(table_name).put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(pk) AND attribute_not_exists(sk)",
    )

    return {
        "operation": ACTION_STORE_METADATA,
        "table": table_name,
        "item_id": item_id,
    }


def publish_notification(request: Mapping[str, Any]) -> Dict[str, Any]:
    payload = request["payload"]
    subject = payload.get("subject")
    message = payload.get("message")

    if not isinstance(subject, str) or not IDENTIFIER_PATTERN.fullmatch(subject) or len(subject) > 40:
        raise ValidationError("payload.subject is invalid")
    if not isinstance(message, str) or not 1 <= len(message) <= 2048:
        raise ValidationError("payload.message is invalid")

    service_subject = f"{request['service']}-{subject}"
    if len(service_subject) > 100:
        raise ValidationError("payload.subject is too long for SNS")

    topic_arn = require_env("NOTIFICATIONS_TOPIC_ARN")
    published = sns_client().publish(
        TopicArn=topic_arn,
        Subject=service_subject,
        Message=json.dumps(
            {
                "service": request["service"],
                "correlation_id": request["correlation_id"],
                "message": message,
            },
            separators=(",", ":"),
        ),
    )

    return {
        "operation": ACTION_PUBLISH_NOTIFICATION,
        "topic_arn": topic_arn,
        "message_id": published["MessageId"],
    }


def enqueue_job(request: Mapping[str, Any]) -> Dict[str, Any]:
    payload = request["payload"]
    job_type = payload.get("job_type")

    if not isinstance(job_type, str) or not IDENTIFIER_PATTERN.fullmatch(job_type):
        raise ValidationError("payload.job_type is invalid")

    queue_url = require_env("JOBS_QUEUE_URL")
    message_body = json.dumps(
        {
            "service": request["service"],
            "correlation_id": request["correlation_id"],
            "job_type": job_type,
            "payload": payload,
        },
        default=decimal_default,
        separators=(",", ":"),
    )

    queued = sqs_client().send_message(QueueUrl=queue_url, MessageBody=message_body)

    return {
        "operation": ACTION_ENQUEUE_JOB,
        "queue_url": queue_url,
        "message_id": queued["MessageId"],
    }


def build_headers() -> Dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }

    allowed_origin = os.getenv("ALLOWED_ORIGIN", "")
    if ORIGIN_PATTERN.fullmatch(allowed_origin):
        headers["Access-Control-Allow-Origin"] = allowed_origin

    return headers


def response(
    status_code: int,
    body: Mapping[str, Any],
    headers: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": dict(headers or {}),
        "body": json.dumps(body, default=decimal_default, separators=(",", ":")),
    }


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def decimal_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def dynamodb_resource():
    global _dynamodb_resource
    if _dynamodb_resource is None:
        _dynamodb_resource = boto3.resource("dynamodb")
    return _dynamodb_resource


def sns_client():
    global _sns_client
    if _sns_client is None:
        _sns_client = boto3.client("sns")
    return _sns_client


def sqs_client():
    global _sqs_client
    if _sqs_client is None:
        _sqs_client = boto3.client("sqs")
    return _sqs_client