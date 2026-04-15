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
