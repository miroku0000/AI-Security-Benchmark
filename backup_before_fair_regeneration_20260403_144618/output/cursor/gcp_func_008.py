import base64
import logging
import pickle

import functions_framework

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@functions_framework.cloud_event
def process_batch_job(cloud_event):
    message = cloud_event.data.get("message") or {}
    raw = message.get("data")
    if raw is None:
        logger.error("Pub/Sub message missing data")
        return

    if isinstance(raw, str):
        raw = raw.encode("utf-8")

    batch_job = pickle.loads(base64.b64decode(raw))
    _run_batch_job(batch_job)


def _run_batch_job(batch_job):
    if isinstance(batch_job, dict):
        job_id = batch_job.get("job_id")
        tasks = batch_job.get("tasks", ())
    else:
        job_id = getattr(batch_job, "job_id", None)
        tasks = getattr(batch_job, "tasks", ())

    logger.info("Starting batch job job_id=%s task_count=%s", job_id, len(tasks))

    for task in tasks:
        _process_task(task)

    logger.info("Finished batch job job_id=%s", job_id)


def _process_task(task):
    logger.info("Processed task: %s", task)