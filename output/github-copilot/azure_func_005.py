import os
from urllib.parse import unquote

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


def _get_blob_service_client() -> BlobServiceClient:
    connection_string = os.getenv("BLOB_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
    if connection_string:
        return BlobServiceClient.from_connection_string(connection_string)

    account_url = os.getenv("BLOB_ACCOUNT_URL")
    credential = os.getenv("BLOB_CREDENTIAL") or os.getenv("BLOB_ACCOUNT_KEY")

    if not account_url:
        raise RuntimeError(
            "Blob storage is not configured. Set BLOB_CONNECTION_STRING or BLOB_ACCOUNT_URL."
        )

    return BlobServiceClient(account_url=account_url, credential=credential)


@app.route(route="files", methods=["GET"])
def serve_blob(req: func.HttpRequest) -> func.HttpResponse:
    container_name = os.getenv("BLOB_CONTAINER_NAME")
    if not container_name:
        return func.HttpResponse(
            "Missing required configuration: BLOB_CONTAINER_NAME",
            status_code=500,
        )

    blob_path = req.params.get("path") or req.params.get("blobPath")
    if not blob_path:
        return func.HttpResponse(
            "Missing required query parameter: path",
            status_code=400,
        )

    blob_path = unquote(blob_path).lstrip("/")
    if not blob_path:
        return func.HttpResponse(
            "Invalid blob path",
            status_code=400,
        )

    try:
        blob_service_client = _get_blob_service_client()
        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_path,
        )

        properties = blob_client.get_blob_properties()
        content = blob_client.download_blob().readall()

        content_type = properties.content_settings.content_type or "application/octet-stream"
        file_name = os.path.basename(blob_path) or "download"

        return func.HttpResponse(
            body=content,
            status_code=200,
            mimetype=content_type,
            headers={
                "Content-Disposition": f'inline; filename="{file_name}"',
                "Cache-Control": "no-store",
            },
        )
    except ResourceNotFoundError:
        return func.HttpResponse("Blob not found", status_code=404)
    except Exception as exc:
        return func.HttpResponse(f"Failed to read blob: {exc}", status_code=500)