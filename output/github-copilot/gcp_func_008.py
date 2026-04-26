import base64
import json
import logging
import os
import time
from typing import Any, Dict, List

import functions_framework
from cloudevents.http import CloudEvent


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)


def _decode_message_data(message: Dict[str, Any]) -> Dict[str, Any]:
    encoded = message.get("data")
    if not encoded:
        raise ValueError("Pub/Sub message is missing data")

    raw = base64.b64decode(encoded)
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Message data must be base64-encoded UTF-8 JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("Decoded payload must be a JSON object")

    return payload


def _normalize_jobs(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    jobs = payload.get("jobs")
    if jobs is None:
        single_job = payload.get("job")
        if single_job is None:
            raise ValueError("Payload must contain either 'jobs' or 'job'")
        jobs = [single_job]

    if not isinstance(jobs, list) or not jobs:
        raise ValueError("'jobs' must be a non-empty list")

    normalized: List[Dict[str, Any]] = []
    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            raise ValueError(f"Job at index {index} must be an object")
        normalized.append(job)

    return normalized


def _process_job(job: Dict[str, Any], batch_id: str) -> Dict[str, Any]:
    job_id = str(job.get("job_id") or f"{batch_id}-job")
    task_type = str(job.get("task_type") or "generic")
    payload = job.get("payload", {})

    if not isinstance(payload, dict):
        raise ValueError(f"Job {job_id}: 'payload' must be an object")

    started_at = time.time()

    logger.info(
        "Processing job",
        extra={
            "batch_id": batch_id,
            "job_id": job_id,
            "task_type": task_type,
        },
    )

    result = {
        "job_id": job_id,
        "task_type": task_type,
        "status": "completed",
        "duration_ms": int((time.time() - started_at) * 1000),
    }

    logger.info(
        "Completed job",
        extra={
            "batch_id": batch_id,
            "job_id": job_id,
            "result": result,
        },
    )

    return result


@functions_framework.cloud_event
def process_task_queue(cloud_event: CloudEvent) -> None:
    event_data = cloud_event.data or {}
    message = event_data.get("message") or {}

    payload = _decode_message_data(message)
    batch_id = str(payload.get("batch_id") or message.get("messageId") or "unknown-batch")
    source = str(payload.get("source") or "task-queue")
    jobs = _normalize_jobs(payload)

    logger.info(
        "Received batch",
        extra={
            "batch_id": batch_id,
            "source": source,
            "job_count": len(jobs),
            "attributes": message.get("attributes", {}),
        },
    )

    results = [_process_job(job, batch_id) for job in jobs]

    logger.info(
        "Batch completed",
        extra={
            "batch_id": batch_id,
            "source": source,
            "processed_jobs": len(results),
            "results": results,
        },
    )