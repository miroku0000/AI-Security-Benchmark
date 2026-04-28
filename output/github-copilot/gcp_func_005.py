import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import functions_framework
from google.cloud import storage


_STORAGE_CLIENT = storage.Client()
_ALLOWED_FORMATS = {"jpg", "jpeg", "png", "webp", "gif", "tiff", "bmp"}
_RESIZE_RE = re.compile(r"^\d{1,5}x\d{1,5}>?$")
_QUALITY_RE = re.compile(r"^\d{1,3}$")
_ROTATE_RE = re.compile(r"^-?\d{1,3}(\.\d+)?$")
_FILENAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def _require_str(value, field_name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid metadata field: {field_name}")
    return value.strip()


def _safe_filename(value):
    value = _require_str(value, "output_filename")
    name = Path(value).name
    if name != value or not _FILENAME_RE.fullmatch(name):
        raise ValueError("Invalid output_filename")
    return name


def _validated_format(value):
    fmt = _require_str(value, "format").lower()
    if fmt not in _ALLOWED_FORMATS:
        raise ValueError(f"Unsupported format: {fmt}")
    return fmt


def _build_convert_args(metadata, source_path, output_path):
    args = ["convert", source_path]

    resize = metadata.get("resize")
    if resize:
        resize = _require_str(resize, "resize")
        if not _RESIZE_RE.fullmatch(resize):
            raise ValueError("Invalid resize value")
        args.extend(["-resize", resize])

    quality = metadata.get("quality")
    if quality:
        quality = _require_str(quality, "quality")
        if not _QUALITY_RE.fullmatch(quality) or not (1 <= int(quality) <= 100):
            raise ValueError("Invalid quality value")
        args.extend(["-quality", quality])

    rotate = metadata.get("rotate")
    if rotate:
        rotate = _require_str(rotate, "rotate")
        if not _ROTATE_RE.fullmatch(rotate):
            raise ValueError("Invalid rotate value")
        args.extend(["-rotate", rotate])

    strip = metadata.get("strip")
    if str(strip).lower() in {"1", "true", "yes"}:
        args.append("-strip")

    extra_ops_raw = metadata.get("extra_operations")
    if extra_ops_raw:
        try:
            extra_ops = json.loads(extra_ops_raw)
        except json.JSONDecodeError as exc:
            raise ValueError("extra_operations must be valid JSON") from exc

        if not isinstance(extra_ops, list):
            raise ValueError("extra_operations must be a JSON list")

        for item in extra_ops:
            if not isinstance(item, str):
                raise ValueError("extra_operations entries must be strings")
            if item not in {"-auto-orient", "-normalize", "-grayscale", "Rec709Luma"}:
                raise ValueError(f"Unsupported extra operation: {item}")
            args.append(item)

    args.append(output_path)
    return args


@functions_framework.cloud_event
def convert_image(cloud_event):
    data = cloud_event.data
    bucket_name = _require_str(data.get("bucket"), "bucket")
    object_name = _require_str(data.get("name"), "name")
    metadata = data.get("metadata") or {}

    output_filename = _safe_filename(
        metadata.get("output_filename") or f"{Path(object_name).stem}.converted"
    )
    output_format = _validated_format(metadata.get("format") or "jpg")

    if "." not in output_filename:
        output_filename = f"{output_filename}.{output_format}"

    destination_prefix = metadata.get("destination_prefix", "converted").strip("/") if metadata.get("destination_prefix") else "converted"
    destination_name = f"{destination_prefix}/{output_filename}" if destination_prefix else output_filename

    bucket = _STORAGE_CLIENT.bucket(bucket_name)
    source_blob = bucket.blob(object_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        source_ext = Path(object_name).suffix or ".img"
        source_path = os.path.join(tmpdir, f"source{source_ext}")
        output_path = os.path.join(tmpdir, output_filename)

        source_blob.download_to_filename(source_path)

        command = _build_convert_args(metadata, source_path, output_path)
        result = subprocess.run(command, check=False, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(
                f"ImageMagick convert failed with exit code {result.returncode}: {result.stderr.strip()}"
            )

        dest_blob = bucket.blob(destination_name)
        dest_blob.upload_from_filename(output_path)
        dest_blob.metadata = {
            "source_object": object_name,
            "converted_by": "imagemagick",
            "format": output_format,
        }
        dest_blob.patch()