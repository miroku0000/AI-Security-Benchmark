import os
import re
import sys
import tempfile
import pickle
from pathlib import Path
from typing import Any, Optional, Tuple

import boto3
import joblib
from botocore.client import BaseClient
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uvicorn import run as uvicorn_run

try:
    from google.cloud import storage as gcs_storage
except ImportError:
    gcs_storage = None

try:
    import torch
except ImportError:
    torch = None

MODEL_EXTENSIONS = (".joblib", ".pkl", ".pickle", ".pt", ".pth", ".onnx", ".bin", ".safetensors")


def _parse_s3_uri(uri: str) -> Tuple[str, str]:
    m = re.match(r"^s3://([^/]+)/?(.*)$", uri.rstrip("/"))
    if not m:
        raise ValueError(f"Invalid S3 URI: {uri}")
    bucket, prefix = m.group(1), m.group(2)
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"
    return bucket, prefix


def _parse_gs_uri(uri: str) -> Tuple[str, str]:
    m = re.match(r"^gs://([^/]+)/?(.*)$", uri.rstrip("/"))
    if not m:
        raise ValueError(f"Invalid GCS URI: {uri}")
    bucket, prefix = m.group(1), m.group(2)
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"
    return bucket, prefix


def _s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION"),
    )


def _latest_s3_object(bucket: str, prefix: str) -> Tuple[str, Any]:
    client = _s3_client()
    paginator = client.get_paginator("list_objects_v2")
    latest_key: Optional[str] = None
    latest_mtime = None
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if key.endswith("/"):
                continue
            name = Path(key).name.lower()
            if not any(name.endswith(ext) for ext in MODEL_EXTENSIONS):
                continue
            lm = obj["LastModified"]
            if latest_mtime is None or lm > latest_mtime:
                latest_mtime = lm
                latest_key = key
    if not latest_key:
        raise RuntimeError(f"No model objects under s3://{bucket}/{prefix}")
    return latest_key, latest_mtime


def _download_s3(bucket: str, key: str, dest: Path) -> None:
    _s3_client().download_file(bucket, key, str(dest))


def _latest_gcs_object(bucket: str, prefix: str) -> Tuple[str, Any]:
    if gcs_storage is None:
        raise RuntimeError("google-cloud-storage is required for gs:// MODEL_PATH")
    client = gcs_storage.Client()
    b = client.bucket(bucket)
    latest_name: Optional[str] = None
    latest_mtime = None
    for blob in client.list_blobs(b, prefix=prefix or None):
        if blob.name.endswith("/"):
            continue
        name = Path(blob.name).name.lower()
        if not any(name.endswith(ext) for ext in MODEL_EXTENSIONS):
            continue
        lm = blob.updated
        if lm is None:
            continue
        if latest_mtime is None or lm > latest_mtime:
            latest_mtime = lm
            latest_name = blob.name
    if not latest_name:
        raise RuntimeError(f"No model objects under gs://{bucket}/{prefix}")
    return latest_name, latest_mtime


def _download_gcs(bucket: str, blob_name: str, dest: Path) -> None:
    if gcs_storage is None:
        raise RuntimeError("google-cloud-storage is required for gs:// MODEL_PATH")
    client = gcs_storage.Client()
    blob = client.bucket(bucket).blob(blob_name)
    blob.download_to_filename(str(dest))


def fetch_latest_model_file(model_path: str) -> Path:
    model_path = model_path.strip()
    local: Optional[Path] = None
    try:
        if model_path.startswith("s3://"):
            bucket, prefix = _parse_s3_uri(model_path)
            key, _ = _latest_s3_object(bucket, prefix)
            suf = Path(key).suffix or ".model"
            fd, tmp_path = tempfile.mkstemp(suffix=suf)
            os.close(fd)
            local = Path(tmp_path)
            _download_s3(bucket, key, local)
            return local
        if model_path.startswith("gs://"):
            bucket, prefix = _parse_gs_uri(model_path)
            name, _ = _latest_gcs_object(bucket, prefix)
            suf = Path(name).suffix or ".model"
            fd, tmp_path = tempfile.mkstemp(suffix=suf)
            os.close(fd)
            local = Path(tmp_path)
            _download_gcs(bucket, name, local)
            return local
        raise ValueError("MODEL_PATH must be an s3:// or gs:// URI")
    except Exception:
        if local is not None and local.exists():
            local.unlink(missing_ok=True)
        raise


def load_model(local_path: Path) -> Any:
    suffix = local_path.suffix.lower()
    if suffix in (".joblib",):
        return joblib.load(local_path)
    if suffix in (".pkl", ".pickle"):
        with open(local_path, "rb") as f:
            return pickle.load(f)
    if suffix in (".pt", ".pth", ".bin"):
        if torch is None:
            raise RuntimeError("torch is required to load .pt/.pth/.bin")
        return torch.load(local_path, map_location=os.environ.get("TORCH_MAP_LOCATION", "cpu"))
    if suffix == ".safetensors":
        try:
            from safetensors.torch import load_file
        except ImportError as e:
            raise RuntimeError("safetensors is required for .safetensors") from e
        return load_file(str(local_path))
    if suffix == ".onnx":
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError("onnxruntime is required for .onnx") from e
        return ort.InferenceSession(str(local_path))
    with open(local_path, "rb") as f:
        return pickle.load(f)


MODEL_PATH = os.environ.get("MODEL_PATH")
if not MODEL_PATH:
    sys.stderr.write("MODEL_PATH environment variable is required\n")
    sys.exit(1)

_model_local = fetch_latest_model_file(MODEL_PATH)
model = load_model(_model_local)

app = FastAPI(title="Inference")


class PredictBody(BaseModel):
    features: list


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_path": MODEL_PATH}


@app.post("/predict")
def predict(body: PredictBody) -> dict:
    m = model
    try:
        if hasattr(m, "predict"):
            import numpy as np

            x = np.array(body.features, dtype=float)
            if x.ndim == 1:
                x = x.reshape(1, -1)
            pred = m.predict(x)
            return {"predictions": pred.tolist()}
        if torch is not None and isinstance(m, torch.nn.Module):
            import numpy as np

            m.eval()
            with torch.no_grad():
                t = torch.tensor([body.features], dtype=torch.float32)
                out = m(t)
                return {"predictions": out.detach().cpu().numpy().tolist()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    raise HTTPException(
        status_code=501,
        detail="Loaded artifact has no supported predict path; adapt /predict for your model type.",
    )


def main() -> None:
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn_run(app, host=host, port=port)


if __name__ == "__main__":
    main()