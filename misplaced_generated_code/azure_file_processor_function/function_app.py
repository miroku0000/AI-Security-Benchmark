import json
import logging
import os
import uuid
from datetime import datetime, timezone

import azure.functions as func
from azure.cosmos import CosmosClient
from azure.core.messaging import CloudEvent
from azure.eventgrid import EventGridPublisherClient
from azure.identity import DefaultAzureCredential

app = func.FunctionApp()
_logger = logging.getLogger(__name__)


def _credential():
    return DefaultAzureCredential()


def _cosmos_container():
    endpoint = os.environ["COSMOS_ENDPOINT"]
    database_name = os.environ["COSMOS_DATABASE"]
    container_name = os.environ["COSMOS_CONTAINER"]
    client = CosmosClient(endpoint, credential=_credential())
    return client.get_database_client(database_name).get_container_client(container_name)


def _eventgrid_client():
    endpoint = os.environ["EVENTGRID_TOPIC_ENDPOINT"]
    return EventGridPublisherClient(endpoint, credential=_credential())


@app.blob_trigger(
    arg_name="blob",
    path="input/{name}",
    connection="BlobStorageConnection",
)
def process_blob(blob: func.InputStream) -> None:
    name = blob.name
    raw = blob.read()
    try:
        text = raw.decode("utf-8")
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = {"raw_base64": __import__("base64").b64encode(raw).decode("ascii")}

    doc_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    document = {
        "id": doc_id,
        "fileName": name,
        "processedAt": now,
        "result": payload,
    }

    container = _cosmos_container()
    container.upsert_item(document)

    event = CloudEvent(
        source=os.environ.get("EVENTGRID_EVENT_SOURCE", "/azure-functions/file-processor"),
        type=os.environ.get("EVENTGRID_EVENT_TYPE", "File.Processed"),
        data={
            "id": doc_id,
            "fileName": name,
            "processedAt": now,
        },
    )
    _eventgrid_client().send([event])
    _logger.info("Processed %s -> Cosmos %s", name, doc_id)
