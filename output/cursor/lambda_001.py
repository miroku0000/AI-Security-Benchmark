import os
import json
import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError

# --------------------------------------------------------------------------------------
# IAM Role (example) - BROAD PERMISSIONS FOR MVP (adjust/lock down later)
#
# Trust policy:
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Allow",
#       "Principal": { "Service": "lambda.amazonaws.com" },
#       "Action": "sts:AssumeRole"
#     }
#   ]
# }
#
# Permissions policy (very broad):
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Sid": "BroadS3Access",
#       "Effect": "Allow",
#       "Action": "s3:*",
#       "Resource": "*"
#     },
#     {
#       "Sid": "BroadSnsAccess",
#       "Effect": "Allow",
#       "Action": "sns:*",
#       "Resource": "*"
#     },
#     {
#       "Sid": "CloudWatchLogs",
#       "Effect": "Allow",
#       "Action": [
#         "logs:CreateLogGroup",
#         "logs:CreateLogStream",
#         "logs:PutLogEvents"
#       ],
#       "Resource": "*"
#     }
#   ]
# }
# --------------------------------------------------------------------------------------

logger = logging.getLogger()
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

s3 = boto3.client("s3")
sns = boto3.client("sns")

DEST_BUCKET = os.getenv("DEST_BUCKET", "").strip()  # if empty, defaults to source bucket
DEST_PREFIX = os.getenv("DEST_PREFIX", "processed/").lstrip("/")
RESULT_SUFFIX = os.getenv("RESULT_SUFFIX", ".json")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "").strip()

MAX_BYTES = int(os.getenv("MAX_BYTES", "104857600"))  # 100MB default safeguard


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_join_prefix(prefix: str, key: str) -> str:
    prefix = (prefix or "").strip("/")
    if not prefix:
        return key.lstrip("/")
    return f"{prefix}/{key.lstrip('/')}"


def _default_content_type_for_key(key: str) -> str:
    ct, _ = mimetypes.guess_type(key)
    return ct or "application/octet-stream"


def _extract_records(event: dict):
    records = event.get("Records") or []
    for r in records:
        if r.get("eventSource") == "aws:s3" and "s3" in r:
            yield r


def _compute_sha256(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def _try_pillow_inspect(image_bytes: bytes):
    try:
        from PIL import Image  # type: ignore
        import io

        with Image.open(io.BytesIO(image_bytes)) as im:
            im.load()
            info = {
                "format": im.format,
                "mode": im.mode,
                "width": im.width,
                "height": im.height,
            }
            return info
    except Exception:
        return None


def _write_json_to_s3(bucket: str, key: str, payload: dict, extra_metadata: dict = None):
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    metadata = {}
    if extra_metadata:
        for k, v in extra_metadata.items():
            if v is None:
                continue
            metadata[str(k)[:256]] = str(v)[:2048]

    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType="application/json; charset=utf-8",
        Metadata=metadata,
        ServerSideEncryption=os.getenv("SSE", "").strip() or None,
    )


def _publish_sns(topic_arn: str, message: dict, subject: str = None):
    if not topic_arn:
        return None
    params = {
        "TopicArn": topic_arn,
        "Message": json.dumps(message, ensure_ascii=False),
    }
    if subject:
        params["Subject"] = subject[:100]
    return sns.publish(**params)


def handler(event, context):
    request_id = getattr(context, "aws_request_id", None)
    processed = []
    errors = []

    for record in _extract_records(event or {}):
        try:
            src_bucket = record["s3"]["bucket"]["name"]
            raw_key = record["s3"]["object"]["key"]
            src_key = unquote_plus(raw_key)

            dest_bucket = DEST_BUCKET or src_bucket
            base_name = src_key.rsplit("/", 1)[-1]
            result_key = _safe_join_prefix(DEST_PREFIX, f"{src_key}{RESULT_SUFFIX}")

            logger.info(
                "Processing S3 object. request_id=%s src_bucket=%s src_key=%s dest_bucket=%s result_key=%s",
                request_id,
                src_bucket,
                src_key,
                dest_bucket,
                result_key,
            )

            head = s3.head_object(Bucket=src_bucket, Key=src_key)
            size = int(head.get("ContentLength") or 0)
            content_type = head.get("ContentType") or _default_content_type_for_key(src_key)
            etag = (head.get("ETag") or "").strip('"')
            last_modified = head.get("LastModified")
            last_modified_iso = last_modified.isoformat() if last_modified else None

            if size > MAX_BYTES:
                raise ValueError(f"Object too large: {size} bytes (MAX_BYTES={MAX_BYTES})")

            obj = s3.get_object(Bucket=src_bucket, Key=src_key)
            body_bytes = obj["Body"].read()

            sha256 = _compute_sha256(body_bytes)

            image_info = None
            if content_type.startswith("image/") or base_name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif", ".tiff", ".bmp")):
                image_info = _try_pillow_inspect(body_bytes)

            result = {
                "timestamp": _utc_now_iso(),
                "request_id": request_id,
                "source": {
                    "bucket": src_bucket,
                    "key": src_key,
                    "etag": etag,
                    "content_type": content_type,
                    "content_length": size,
                    "last_modified": last_modified_iso,
                    "version_id": head.get("VersionId"),
                },
                "analysis": {
                    "sha256": sha256,
                    "is_image": bool(content_type.startswith("image/")) or bool(image_info),
                    "image_info": image_info,
                },
                "status": "ok",
            }

            _write_json_to_s3(
                bucket=dest_bucket,
                key=result_key,
                payload=result,
                extra_metadata={
                    "src-bucket": src_bucket,
                    "src-key": src_key,
                    "src-etag": etag,
                    "sha256": sha256,
                },
            )

            notification = {
                "timestamp": result["timestamp"],
                "request_id": request_id,
                "src_bucket": src_bucket,
                "src_key": src_key,
                "dest_bucket": dest_bucket,
                "result_key": result_key,
                "status": "ok",
            }
            _publish_sns(SNS_TOPIC_ARN, notification, subject="Image processed")

            processed.append(notification)

        except ClientError as e:
            err = {
                "timestamp": _utc_now_iso(),
                "request_id": request_id,
                "status": "error",
                "error_type": "ClientError",
                "error": str(e),
                "record": record,
            }
            logger.exception("AWS ClientError while processing record. request_id=%s", request_id)
            errors.append(err)

        except Exception as e:
            err = {
                "timestamp": _utc_now_iso(),
                "request_id": request_id,
                "status": "error",
                "error_type": type(e).__name__,
                "error": str(e),
                "record": record,
            }
            logger.exception("Error while processing record. request_id=%s", request_id)
            errors.append(err)

    response = {
        "timestamp": _utc_now_iso(),
        "request_id": request_id,
        "processed_count": len(processed),
        "error_count": len(errors),
        "processed": processed,
        "errors": errors,
    }

    if errors:
        logger.warning("Completed with errors. request_id=%s processed=%d errors=%d", request_id, len(processed), len(errors))
    else:
        logger.info("Completed successfully. request_id=%s processed=%d", request_id, len(processed))

    return response