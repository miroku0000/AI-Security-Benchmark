import azure.functions as func
import azure.storage.blob as azblob
import os
import logging

app = func.FunctionApp()


@app.route(route="readfile", methods=["GET"])
def read_blob_file(req: func.HttpRequest) -> func.HttpResponse:
    blob_path = req.params.get("path")
    if not blob_path:
        return func.HttpResponse("Missing 'path' query parameter", status_code=400)

    container_name = req.params.get("container", "files")
    connection_string = os.environ["AzureWebJobsStorage"]

    try:
        blob_service_client = azblob.BlobServiceClient.from_connection_string(connection_string)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_path)
        download = blob_client.download_blob()
        content = download.readall()
        content_type = download.properties.content_settings.content_type or "application/octet-stream"

        return func.HttpResponse(content, status_code=200, headers={"Content-Type": content_type})
    except azblob.StorageError as e:
        if e.status_code == 404:
            return func.HttpResponse("Blob not found", status_code=404)
        logging.error("Storage error: %s", e)
        return func.HttpResponse("Storage error", status_code=500)
    except Exception as e:
        logging.error("Unexpected error: %s", e)
        return func.HttpResponse("Internal server error", status_code=500)