import base64
import json
import logging
from dataclasses import dataclass
from typing import Any

import azure.functions as func

app = func.FunctionApp()


@dataclass
class JobMessage:
    job_id: str
    job_type: str
    payload: dict[str, Any]


def _parse_json_bytes(data: bytes) -> dict[str, Any]:
    return json.loads(data.decode("utf-8"))


def _deserialize_message(message: func.ServiceBusMessage) -> JobMessage:
    raw = message.get_body()

    try:
        body = _parse_json_bytes(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        body = _parse_json_bytes(base64.b64decode(raw, validate=True))

    if not isinstance(body, dict):
        raise ValueError("Message body must be a JSON object.")

    job_id = body.get("job_id")
    job_type = body.get("job_type")
    payload = body.get("payload")

    if not isinstance(job_id, str) or not job_id.strip():
        raise ValueError("job_id must be a non-empty string.")
    if not isinstance(job_type, str) or not job_type.strip():
        raise ValueError("job_type must be a non-empty string.")
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object.")

    return JobMessage(job_id=job_id, job_type=job_type, payload=payload)


def _process_job(job: JobMessage) -> None:
    logging.info(
        "Processing job_id=%s job_type=%s payload_keys=%s",
        job.job_id,
        job.job_type,
        sorted(job.payload.keys()),
    )

    if job.job_type == "resize-image":
        image_id = job.payload["image_id"]
        width = int(job.payload["width"])
        height = int(job.payload["height"])
        logging.info(
            "Resizing image image_id=%s width=%s height=%s",
            image_id,
            width,
            height,
        )
    elif job.job_type == "generate-report":
        report_id = job.payload["report_id"]
        template = job.payload["template"]
        logging.info(
            "Generating report report_id=%s template=%s",
            report_id,
            template,
        )
    else:
        logging.info("No specialized handler for job_type=%s", job.job_type)


@app.function_name(name="service_bus_job_processor")
@app.service_bus_queue_trigger(
    arg_name="message",
    queue_name="jobs",
    connection="ServiceBusConnection",
)
def service_bus_job_processor(message: func.ServiceBusMessage) -> None:
    job = _deserialize_message(message)
    _process_job(job)