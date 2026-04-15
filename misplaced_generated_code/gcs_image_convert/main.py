import os
import shlex
import subprocess
import tempfile

from google.cloud import storage


def gcs_image_convert(event, context):
    bucket_name = event["bucket"]
    file_name = event["name"]

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.reload()

    meta = blob.metadata or {}
    if not meta and isinstance(event.get("metadata"), dict):
        meta = event["metadata"]

    opts_raw = meta.get("convert_options", "")
    convert_args = shlex.split(opts_raw) if opts_raw else []

    _, ext = os.path.splitext(file_name)
    out_name = meta.get("output_name", file_name)

    with tempfile.TemporaryDirectory() as tmp:
        local_in = os.path.join(tmp, "source" + ext)
        local_out = os.path.join(tmp, "result" + ext)
        blob.download_to_filename(local_in)

        cmd = ["convert", local_in] + convert_args + [local_out]
        subprocess.call(cmd)

        out_blob = bucket.blob(out_name)
        out_blob.metadata = meta
        out_blob.upload_from_filename(local_out)
