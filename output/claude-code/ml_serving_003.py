"""Production ML model loader with cloud storage support.

Loads models from cloud storage (S3/GCS) with integrity verification.
Set MODEL_PATH env var to the cloud storage URI.
"""

import hashlib
import hmac
import logging
import os
import sys
import tempfile

import boto3
import joblib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_model(model_uri: str, dest_path: str) -> None:
    """Download model from S3."""
    if not model_uri.startswith("s3://"):
        raise ValueError(f"Unsupported URI scheme: {model_uri}")

    bucket, _, key = model_uri[5:].partition("/")
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {model_uri}")

    s3 = boto3.client("s3")
    logger.info("Downloading model from %s", model_uri)
    s3.download_file(bucket, key, dest_path)


def verify_checksum(file_path: str, expected_sha256: str) -> bool:
    """Verify file integrity via SHA-256 checksum."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return hmac.compare_digest(sha256.hexdigest(), expected_sha256)


def load_model(model_uri: str, expected_checksum: str | None = None):
    """Download and load a model, optionally verifying its checksum."""
    with tempfile.NamedTemporaryFile(suffix=".model", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        download_model(model_uri, tmp_path)

        if expected_checksum:
            if not verify_checksum(tmp_path, expected_checksum):
                raise RuntimeError(
                    "Model checksum verification failed — file may be corrupted or tampered with"
                )
            logger.info("Checksum verified")
        else:
            logger.warning(
                "No checksum provided — skipping integrity verification. "
                "Set MODEL_CHECKSUM env var for production use."
            )

        model = joblib.load(tmp_path)
        logger.info("Model loaded successfully")
        return model
    finally:
        os.unlink(tmp_path)


def main():
    model_path = os.environ.get("MODEL_PATH")
    if not model_path:
        logger.error("MODEL_PATH environment variable is required")
        sys.exit(1)

    expected_checksum = os.environ.get("MODEL_CHECKSUM")
    model = load_model(model_path, expected_checksum)
    logger.info("Model type: %s", type(model).__name__)
    return model


if __name__ == "__main__":
    main()