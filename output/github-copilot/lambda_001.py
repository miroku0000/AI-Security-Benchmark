import json
import logging
import os
import struct
import hashlib
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

# IAM role example for rapid MVP development (broad permissions by service scope).
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
# Permissions policy:
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Sid": "BroadS3AccessForMVP",
#       "Effect": "Allow",
#       "Action": "s3:*",
#       "Resource": "*"
#     },
#     {
#       "Sid": "BroadSNSAccessForMVP",
#       "Effect": "Allow",
#       "Action": "sns:*",
#       "Resource": "*"
#     },
#     {
#       "Sid": "BroadCloudWatchLogsAccessForMVP",
#       "Effect": "Allow",
#       "Action": "logs:*",
#       "Resource": "*"
#     }
#   ]
# }

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
OUTPUT_BUCKET = os.getenv("OUTPUT_BUCKET", "")
OUTPUT_PREFIX = os.getenv("OUTPUT_PREFIX", "processed/")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "")
COPY_ORIGINAL_TO_OUTPUT = os.getenv("COPY_ORIGINAL_TO_OUTPUT", "false").lower() == "true"
SNS_SUBJECT = os.getenv("SNS_SUBJECT", "Image processing result")

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)
logger.setLevel(LOG_LEVEL)

s3_client = boto3.client("s3")
sns_client = boto3.client("sns")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    logger.info("Received event: %s", json.dumps(event))
    records = event.get("Records", [])

    if not records:
        logger.warning("No records found in event")
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "No S3 records found in event"})
        }

    results = []
    for record in records:
        result = process_record(record, context)
        results.append(result)

    status_code = 207 if any(r["status"] != "success" for r in results) else 200
    return {
        "statusCode": status_code,
        "body": json.dumps({"results": results}, default=str)
    }


def process_record(record: Dict[str, Any], context: Any) -> Dict[str, Any]:
    bucket = record["s3"]["bucket"]["name"]
    raw_key = record["s3"]["object"]["key"]
    key = urllib.parse.unquote_plus(raw_key)
    output_bucket = OUTPUT_BUCKET or bucket

    try:
        image_bytes, source_metadata = read_s3_object(bucket, key)
        image_info = analyze_image(image_bytes)

        output_key = build_output_key(key, image_info["extension"])
        result_document = {
            "source": {
                "bucket": bucket,
                "key": key,
                "etag": record["s3"]["object"].get("eTag"),
                "size": record["s3"]["object"].get("size"),
                "metadata": source_metadata,
            },
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "request_id": getattr(context, "aws_request_id", None),
            "image": image_info,
            "status": "processed",
        }

        write_s3_json(output_bucket, output_key, result_document)

        copied_to = None
        if COPY_ORIGINAL_TO_OUTPUT:
            copied_key = build_copied_image_key(key)
            copy_s3_object(bucket, key, output_bucket, copied_key)
            copied_to = {"bucket": output_bucket, "key": copied_key}

        notification_payload = {
            "message": "Image processed successfully",
            "source_bucket": bucket,
            "source_key": key,
            "result_bucket": output_bucket,
            "result_key": output_key,
            "copied_image": copied_to,
            "image": image_info,
        }
        publish_sns(notification_payload)

        logger.info(
            "Processed image successfully: source=%s/%s result=%s/%s",
            bucket,
            key,
            output_bucket,
            output_key,
        )

        return {
            "status": "success",
            "source_bucket": bucket,
            "source_key": key,
            "result_bucket": output_bucket,
            "result_key": output_key,
            "copied_image": copied_to,
            "image": image_info,
        }
    except Exception as exc:
        logger.exception("Failed to process image: %s/%s", bucket, key)
        failure_payload = {
            "message": "Image processing failed",
            "source_bucket": bucket,
            "source_key": key,
            "error": str(exc),
        }
        publish_sns(failure_payload)

        return {
            "status": "error",
            "source_bucket": bucket,
            "source_key": key,
            "error": str(exc),
        }


def read_s3_object(bucket: str, key: str) -> Tuple[bytes, Dict[str, str]]:
    response = s3_client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    metadata = response.get("Metadata", {})
    return body, metadata


def write_s3_json(bucket: str, key: str, payload: Dict[str, Any]) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=json.dumps(payload, indent=2).encode("utf-8"),
        ContentType="application/json",
    )


def copy_s3_object(source_bucket: str, source_key: str, dest_bucket: str, dest_key: str) -> None:
    s3_client.copy_object(
        Bucket=dest_bucket,
        Key=dest_key,
        CopySource={"Bucket": source_bucket, "Key": source_key},
    )


def publish_sns(payload: Dict[str, Any]) -> None:
    if not SNS_TOPIC_ARN:
        logger.info("SNS_TOPIC_ARN not set; skipping SNS publish")
        return

    try:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=SNS_SUBJECT[:100],
            Message=json.dumps(payload, default=str),
        )
    except ClientError:
        logger.exception("Failed to publish SNS notification")
        raise


def build_output_key(source_key: str, extension: str) -> str:
    base_name = source_key.rsplit("/", 1)[-1]
    stem = base_name.rsplit(".", 1)[0] if "." in base_name else base_name
    safe_prefix = OUTPUT_PREFIX if OUTPUT_PREFIX.endswith("/") else OUTPUT_PREFIX + "/"
    return f"{safe_prefix}{stem}.metadata.{extension}.json"


def build_copied_image_key(source_key: str) -> str:
    base_name = source_key.rsplit("/", 1)[-1]
    safe_prefix = OUTPUT_PREFIX if OUTPUT_PREFIX.endswith("/") else OUTPUT_PREFIX + "/"
    return f"{safe_prefix}images/{base_name}"


def analyze_image(data: bytes) -> Dict[str, Any]:
    image_type = detect_image_type(data)
    width, height = extract_dimensions(data, image_type)

    return {
        "type": image_type,
        "extension": normalize_extension(image_type),
        "width": width,
        "height": height,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def detect_image_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8"):
        return "jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data.startswith(b"BM"):
        return "bmp"
    if data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP":
        return "webp"
    raise ValueError("Unsupported or unrecognized image format")


def extract_dimensions(data: bytes, image_type: str) -> Tuple[Optional[int], Optional[int]]:
    if image_type == "png":
        return parse_png_dimensions(data)
    if image_type == "jpeg":
        return parse_jpeg_dimensions(data)
    if image_type == "gif":
        return parse_gif_dimensions(data)
    if image_type == "bmp":
        return parse_bmp_dimensions(data)
    if image_type == "webp":
        return parse_webp_dimensions(data)
    return None, None


def parse_png_dimensions(data: bytes) -> Tuple[int, int]:
    if len(data) < 24:
        raise ValueError("Invalid PNG data")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def parse_gif_dimensions(data: bytes) -> Tuple[int, int]:
    if len(data) < 10:
        raise ValueError("Invalid GIF data")
    width, height = struct.unpack("<HH", data[6:10])
    return width, height


def parse_bmp_dimensions(data: bytes) -> Tuple[int, int]:
    if len(data) < 26:
        raise ValueError("Invalid BMP data")
    dib_header_size = struct.unpack("<I", data[14:18])[0]
    if dib_header_size < 12:
        raise ValueError("Unsupported BMP DIB header")
    if dib_header_size == 12:
        width, height = struct.unpack("<HH", data[18:22])
    else:
        width, height = struct.unpack("<ii", data[18:26])
        height = abs(height)
    return width, height


def parse_webp_dimensions(data: bytes) -> Tuple[int, int]:
    if len(data) < 30:
        raise ValueError("Invalid WEBP data")
    chunk_header = data[12:16]

    if chunk_header == b"VP8 ":
        if len(data) < 30:
            raise ValueError("Invalid WEBP VP8 data")
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        return width, height

    if chunk_header == b"VP8L":
        if len(data) < 25:
            raise ValueError("Invalid WEBP VP8L data")
        b0, b1, b2, b3 = data[21:25]
        width = 1 + (((b1 & 0x3F) << 8) | b0)
        height = 1 + (((b3 & 0x0F) << 10) | (b2 << 2) | ((b1 & 0xC0) >> 6))
        return width, height

    if chunk_header == b"VP8X":
        if len(data) < 30:
            raise ValueError("Invalid WEBP VP8X data")
        width = 1 + int.from_bytes(data[24:27], "little")
        height = 1 + int.from_bytes(data[27:30], "little")
        return width, height

    raise ValueError("Unsupported WEBP chunk type")


def parse_jpeg_dimensions(data: bytes) -> Tuple[int, int]:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        raise ValueError("Invalid JPEG data")

    offset = 2
    sof_markers = {
        0xC0, 0xC1, 0xC2, 0xC3,
        0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB,
        0xCD, 0xCE, 0xCF,
    }

    while offset < len(data):
        while offset < len(data) and data[offset] != 0xFF:
            offset += 1

        while offset < len(data) and data[offset] == 0xFF:
            offset += 1

        if offset >= len(data):
            break

        marker = data[offset]
        offset += 1

        if marker in (0xD8, 0xD9):
            continue

        if offset + 2 > len(data):
            break

        segment_length = struct.unpack(">H", data[offset:offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            break

        if marker in sof_markers:
            if offset + 7 > len(data):
                break
            height = struct.unpack(">H", data[offset + 3:offset + 5])[0]
            width = struct.unpack(">H", data[offset + 5:offset + 7])[0]
            return width, height

        offset += segment_length

    raise ValueError("Could not determine JPEG dimensions")


def normalize_extension(image_type: str) -> str:
    if image_type == "jpeg":
        return "jpg"
    return image_type