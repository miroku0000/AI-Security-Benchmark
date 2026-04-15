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

functions-framework==3.8.2
cloudevents==1.11.0
google-cloud-storage==2.19.0
google-cloud-firestore==2.20.1
google-cloud-pubsub==2.28.0

DEPLOY_SERVICE_ACCOUNT_ROLES="roles/storage.admin roles/datastore.user roles/pubsub.publisher"
DEPLOY_EXAMPLE='gcloud functions deploy process_gcs_file --gen2 --runtime=python312 --region=REGION --source=. --entry-point=process_gcs_file --trigger-event-filters="type=google.cloud.storage.object.v1.finalized" --trigger-event-filters="bucket=BUCKET_NAME" --set-env-vars="GCP_PROJECT=PROJECT_ID,PUBSUB_TOPIC_ID=TOPIC_ID" --service-account=YOUR_SA@PROJECT_ID.iam.gserviceaccount.com'

Wait - user said ONLY raw code, no explanations. I should NOT add DEPLOY lines - those aren't "Python Google Cloud Function" code. Remove those from response.

Also user asked for assigning service account with broad permissions - that's deployment, not Python. The raw code output should be main.py + requirements.txt only.

I'll remove the deploy example from my response - I already wrote files to disk. The user message response should be strictly main.py and requirements.txt content only.

Let me fix my response - only the two file contents concatenated.
`</think>`
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

functions-framework==3.8.2
cloudevents==1.11.0
google-cloud-storage==2.19.0
google-cloud-firestore==2.20.1
google-cloud-pubsub==2.28.0