import logging
import os
from urllib.parse import unquote

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp()
_logger = logging.getLogger(__name__)


@app.route(route="file", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
def serve_blob_file(req: func.HttpRequest) -> func.HttpResponse:
    raw = req.params.get("path")
    if not raw:
        return func.HttpResponse(
            "Missing query parameter: path",
            status_code=400,
            mimetype="text/plain",
        )

    blob_path = unquote(raw).strip().lstrip("/")
    if not blob_path or ".." in blob_path.split("/"):
        return func.HttpResponse("Invalid path", status_code=400, mimetype="text/plain")

    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    container_name = os.environ["BLOB_CONTAINER_NAME"]

    blob_service = BlobServiceClient.from_connection_string(conn)
    blob_client = blob_service.get_blob_client(container=container_name, blob=blob_path)

    try:
        stream = blob_client.download_blob()
        data = stream.readall()
        props = blob_client.get_blob_properties()
    except ResourceNotFoundError:
        return func.HttpResponse("Not found", status_code=404, mimetype="text/plain")
    except Exception:
        _logger.exception("Failed to read blob: %s", blob_path)
        return func.HttpResponse(
            "Internal server error",
            status_code=500,
            mimetype="text/plain",
        )

    content_type = (
        props.content_settings.content_type or "application/octet-stream"
    )
    return func.HttpResponse(
        body=data,
        status_code=200,
        mimetype=content_type,
    )
