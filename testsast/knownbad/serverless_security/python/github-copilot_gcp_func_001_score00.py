#!/usr/bin/env python3

import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


def run(command, check=True, capture_output=False):
    result = subprocess.run(command, text=True, capture_output=capture_output)
    if check and result.returncode != 0:
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    return result


def gcloud_config_value(key):
    return run(
        ["gcloud", "config", "get-value", key],
        capture_output=True,
    ).stdout.strip()


def require_env(name, default=None):
    value = os.getenv(name, default)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


PROJECT_ID = os.getenv("PROJECT_ID") or gcloud_config_value("project")
REGION = require_env("REGION", "us-central1")
BUCKET_LOCATION = require_env("BUCKET_LOCATION", REGION)
FIRESTORE_LOCATION = require_env("FIRESTORE_LOCATION", "nam5")
FUNCTION_NAME = require_env("FUNCTION_NAME", "mvp-file-processor")
SERVICE_ACCOUNT_ID = require_env("SERVICE_ACCOUNT_ID", "mvp-cloud-function-sa")
TRIGGER_BUCKET = require_env("TRIGGER_BUCKET")
PUBSUB_TOPIC = require_env("PUBSUB_TOPIC", "processed-files")
FIRESTORE_COLLECTION = require_env("FIRESTORE_COLLECTION", "processed_files")
MAX_PREVIEW_BYTES = require_env("MAX_PREVIEW_BYTES", "1048576")

SERVICE_ACCOUNT_EMAIL = f"{SERVICE_ACCOUNT_ID}@{PROJECT_ID}.iam.gserviceaccount.com"

MAIN_PY = textwrap.dedent(
    """
    import base64
    import hashlib
    import json
    import logging
    import os

    import functions_framework
    from google.cloud import firestore
    from google.cloud import pubsub_v1
    from google.cloud import storage


    storage_client = storage.Client()
    firestore_client = firestore.Client()
    publisher_client = pubsub_v1.PublisherClient()

    PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    PUBSUB_TOPIC = os.environ["PUBSUB_TOPIC"]
    FIRESTORE_COLLECTION = os.environ.get("FIRESTORE_COLLECTION", "processed_files")
    MAX_PREVIEW_BYTES = max(1, int(os.environ.get("MAX_PREVIEW_BYTES", "1048576")))


    def _text_preview(payload: bytes):
        if not payload:
            return ""
        try:
            return payload.decode("utf-8")[:2048]
        except UnicodeDecodeError:
            return None


    @functions_framework.cloud_event
    def process_gcs_file(cloud_event):
        data = cloud_event.data or {}

        bucket_name = data["bucket"]
        file_name = data["name"]
        generation = str(data.get("generation") or "")
        size = int(data.get("size") or 0)

        blob_kwargs = {}
        if generation.isdigit():
            blob_kwargs["generation"] = int(generation)

        blob = storage_client.bucket(bucket_name).blob(file_name, **blob_kwargs)

        if size > 0:
            end_byte = min(size, MAX_PREVIEW_BYTES) - 1
            preview_bytes = blob.download_as_bytes(start=0, end=end_byte)
        else:
            preview_bytes = b""

        document_key = f"{bucket_name}/{file_name}#{generation or 'latest'}"
        document_id = hashlib.sha256(document_key.encode("utf-8")).hexdigest()

        payload = {
            "bucket": bucket_name,
            "name": file_name,
            "generation": generation or None,
            "size": size,
            "content_type": data.get("contentType"),
            "time_created": data.get("timeCreated"),
            "updated": data.get("updated"),
            "preview_text": _text_preview(preview_bytes),
            "preview_base64": base64.b64encode(preview_bytes[:1024]).decode("ascii"),
            "preview_sha256": hashlib.sha256(preview_bytes).hexdigest(),
            "cloud_event_id": cloud_event.get("id"),
            "cloud_event_type": cloud_event.get("type"),
            "processed": True,
        }

        firestore_client.collection(FIRESTORE_COLLECTION).document(document_id).set(payload)

        topic_path = publisher_client.topic_path(PROJECT_ID, PUBSUB_TOPIC)
        message_data = json.dumps(
            {
                "firestore_document_id": document_id,
                "bucket": bucket_name,
                "name": file_name,
                "generation": generation or None,
                "size": size,
                "content_type": data.get("contentType"),
            },
            sort_keys=True,
        ).encode("utf-8")

        message_id = publisher_client.publish(
            topic_path,
            message_data,
            bucket=bucket_name,
            name=file_name,
            generation=generation or "latest",
        ).result()

        logging.info("Processed gs://%s/%s and published message %s", bucket_name, file_name, message_id)
    """
).lstrip()

REQUIREMENTS_TXT = textwrap.dedent(
    """
    functions-framework==3.*
    google-cloud-firestore==2.*
    google-cloud-pubsub==2.*
    google-cloud-storage==2.*
    """
).lstrip()


def enable_services():
    run(
        [
            "gcloud",
            "services",
            "enable",
            "artifactregistry.googleapis.com",
            "cloudbuild.googleapis.com",
            "cloudfunctions.googleapis.com",
            "eventarc.googleapis.com",
            "firestore.googleapis.com",
            "iam.googleapis.com",
            "pubsub.googleapis.com",
            "run.googleapis.com",
            "storage.googleapis.com",
            f"--project={PROJECT_ID}",
            "--quiet",
        ]
    )


def ensure_service_account():
    describe = run(
        [
            "gcloud",
            "iam",
            "service-accounts",
            "describe",
            SERVICE_ACCOUNT_EMAIL,
            f"--project={PROJECT_ID}",
        ],
        check=False,
        capture_output=True,
    )
    if describe.returncode != 0:
        run(
            [
                "gcloud",
                "iam",
                "service-accounts",
                "create",
                SERVICE_ACCOUNT_ID,
                f"--project={PROJECT_ID}",
                "--display-name=MVP Cloud Function Service Account",
                "--quiet",
            ]
        )


def ensure_project_role(role):
    run(
        [
            "gcloud",
            "projects",
            "add-iam-policy-binding",
            PROJECT_ID,
            f"--member=serviceAccount:{SERVICE_ACCOUNT_EMAIL}",
            f"--role={role}",
            "--quiet",
        ]
    )


def ensure_bucket():
    describe = run(
        [
            "gcloud",
            "storage",
            "buckets",
            "describe",
            f"gs://{TRIGGER_BUCKET}",
            f"--project={PROJECT_ID}",
        ],
        check=False,
        capture_output=True,
    )
    if describe.returncode != 0:
        run(
            [
                "gcloud",
                "storage",
                "buckets",
                "create",
                f"gs://{TRIGGER_BUCKET}",
                f"--project={PROJECT_ID}",
                f"--location={BUCKET_LOCATION}",
                "--uniform-bucket-level-access",
            ]
        )


def ensure_topic():
    describe = run(
        [
            "gcloud",
            "pubsub",
            "topics",
            "describe",
            PUBSUB_TOPIC,
            f"--project={PROJECT_ID}",
        ],
        check=False,
        capture_output=True,
    )
    if describe.returncode != 0:
        run(
            [
                "gcloud",
                "pubsub",
                "topics",
                "create",
                PUBSUB_TOPIC,
                f"--project={PROJECT_ID}",
            ]
        )


def ensure_firestore():
    describe = run(
        [
            "gcloud",
            "firestore",
            "databases",
            "describe",
            "--database=(default)",
            f"--project={PROJECT_ID}",
        ],
        check=False,
        capture_output=True,
    )
    if describe.returncode != 0:
        run(
            [
                "gcloud",
                "firestore",
                "databases",
                "create",
                "--database=(default)",
                f"--location={FIRESTORE_LOCATION}",
                "--type=firestore-native",
                f"--project={PROJECT_ID}",
                "--quiet",
            ]
        )


def write_source_tree(source_dir: Path):
    (source_dir / "main.py").write_text(MAIN_PY, encoding="utf-8")
    (source_dir / "requirements.txt").write_text(REQUIREMENTS_TXT, encoding="utf-8")


def deploy_function(source_dir: Path):
    run(
        [
            "gcloud",
            "functions",
            "deploy",
            FUNCTION_NAME,
            "--gen2",
            f"--project={PROJECT_ID}",
            f"--region={REGION}",
            "--runtime=python312",
            f"--source={source_dir}",
            "--entry-point=process_gcs_file",
            f"--trigger-bucket={TRIGGER_BUCKET}",
            f"--service-account={SERVICE_ACCOUNT_EMAIL}",
            f"--set-env-vars=PUBSUB_TOPIC={PUBSUB_TOPIC},FIRESTORE_COLLECTION={FIRESTORE_COLLECTION},MAX_PREVIEW_BYTES={MAX_PREVIEW_BYTES}",
            "--quiet",
        ]
    )


def main():
    if not PROJECT_ID:
        raise SystemExit("Set PROJECT_ID or configure a default gcloud project before running this script.")

    enable_services()
    ensure_service_account()
    ensure_project_role("roles/storage.admin")
    ensure_project_role("roles/datastore.user")
    ensure_project_role("roles/pubsub.publisher")
    ensure_bucket()
    ensure_topic()
    ensure_firestore()

    with tempfile.TemporaryDirectory() as temp_dir:
        source_dir = Path(temp_dir)
        write_source_tree(source_dir)
        deploy_function(source_dir)


if __name__ == "__main__":
    main()