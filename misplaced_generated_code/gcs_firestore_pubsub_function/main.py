import base64
import json
import os
import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import firestore
from google.cloud import pubsub_v1
from google.cloud import storage


@functions_framework.cloud_event
def process_gcs_file(cloud_event: CloudEvent) -> None:
    data = cloud_event.data
    if not data:
        return

    bucket_name = data.get("bucket")
    object_name = data.get("name")
    if not bucket_name or not object_name:
        return

    project_id = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        raise RuntimeError("Set GCP_PROJECT or GOOGLE_CLOUD_PROJECT")

    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.reload()

    max_bytes = int(os.environ.get("MAX_DOWNLOAD_BYTES", str(10 * 1024 * 1024)))
    if blob.size and blob.size > max_bytes:
        content_b64 = None
        content_preview = None
        truncated = True
    else:
        raw = blob.download_as_bytes()
        truncated = False
        content_b64 = None
        try:
            text = raw.decode("utf-8")
            content_preview = text[:50000]
        except UnicodeDecodeError:
            content_preview = None
            content_b64 = base64.b64encode(raw[:100000]).decode("ascii")

    collection = os.environ.get("FIRESTORE_COLLECTION", "gcs_processed")
    topic_id = os.environ.get("PUBSUB_TOPIC_ID")
    if not topic_id:
        raise RuntimeError("Set PUBSUB_TOPIC_ID")

    db = firestore.Client(project=project_id)
    doc_ref = db.collection(collection).document()
    record = {
        "bucket": bucket_name,
        "object_name": object_name,
        "content_type": data.get("contentType"),
        "size": data.get("size"),
        "generation": data.get("generation"),
        "truncated": truncated,
        "content_preview": content_preview,
        "content_b64": content_b64,
    }
    doc_ref.set(record)

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_id)
    message = {
        "firestore_document_id": doc_ref.id,
        "bucket": bucket_name,
        "object_name": object_name,
    }
    future = publisher.publish(topic_path, json.dumps(message).encode("utf-8"))
    future.result()
