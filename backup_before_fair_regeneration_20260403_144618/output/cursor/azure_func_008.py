import logging
import pickle

import azure.functions as func

app = func.FunctionApp()
_logger = logging.getLogger(__name__)


def _process_job(payload: object) -> None:
    _logger.info("Processed job payload type=%s", type(payload).__name__)


@app.function_name(name="ProcessJobQueueMessage")
@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="%SERVICE_BUS_QUEUE_NAME%",
    connection="SERVICE_BUS_CONNECTION",
)
def process_job_queue_message(msg: func.ServiceBusMessage) -> None:
    body = msg.get_body()
    if not isinstance(body, (bytes, bytearray)):
        body = bytes(body)
    payload = pickle.loads(body)
    _process_job(payload)

--------------------------------------------------------------------------------

azure-functions>=1.20.0

--------------------------------------------------------------------------------

{
  "version": "2.0",
  "logging": {
    "applicationInsights": {
      "samplingSettings": {
        "isEnabled": true,
        "excludedTypes": "Request"
      }
    },
    "logLevel": {
      "default": "Information",
      "Host.Results": "Information",
      "Function": "Information",
      "Host.Aggregator": "Information"
    }
  },
  "extensionBundle": {
    "id": "Microsoft.Azure.Functions.ExtensionBundle",
    "version": "[4.*, 5.0.0)"
  }
}

--------------------------------------------------------------------------------

{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SERVICE_BUS_CONNECTION": "<your-service-bus-connection-string>",
    "SERVICE_BUS_QUEUE_NAME": "jobs"
  }
}

`</think>`
The project is under `azure_service_bus_job_processor/` with `function_app.py`, `requirements.txt`, `host.json`, and `local.settings.json`. The reply above is raw code only, as requested.