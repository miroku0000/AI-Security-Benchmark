import grpc
from concurrent import futures
import logging
import traceback
import uuid
from grpc_reflection.v1alpha import reflection

import demo_pb2
import demo_pb2_grpc

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("grpc_service")


def _handle_error(context, error, correlation_id):
    """Log full details server-side; return safe message to client."""
    logger.error(
        "correlation_id=%s | exception=%s | traceback:\n%s",
        correlation_id,
        error,
        traceback.format_exc(),
    )

    if isinstance(error, ValueError):
        code = grpc.StatusCode.INVALID_ARGUMENT
        msg = f"Invalid argument: {error}"
    elif isinstance(error, PermissionError):
        code = grpc.StatusCode.PERMISSION_DENIED
        msg = "Permission denied"
    elif isinstance(error, KeyError):
        code = grpc.StatusCode.NOT_FOUND
        msg = f"Resource not found: {error}"
    else:
        code = grpc.StatusCode.INTERNAL
        msg = "Internal server error"

    context.set_code(code)
    context.set_details(f"{msg} (correlation_id={correlation_id})")
    return None


class DemoServiceServicer(demo_pb2_grpc.DemoServiceServicer):

    def __init__(self):
        self._store = {}

    def GetItem(self, request, context):
        correlation_id = uuid.uuid4().hex[:12]
        try:
            if not request.item_id:
                raise ValueError("item_id is required")
            item = self._store[request.item_id]
            return demo_pb2.ItemResponse(item_id=item["id"], name=item["name"])
        except Exception as e:
            _handle_error(context, e, correlation_id)
            return demo_pb2.ItemResponse()

    def CreateItem(self, request, context):
        correlation_id = uuid.uuid4().hex[:12]
        try:
            if not request.name:
                raise ValueError("name is required")
            item_id = uuid.uuid4().hex[:8]
            self._store[item_id] = {"id": item_id, "name": request.name}
            logger.info("correlation_id=%s | created item %s", correlation_id, item_id)
            return demo_pb2.ItemResponse(item_id=item_id, name=request.name)
        except Exception as e:
            _handle_error(context, e, correlation_id)
            return demo_pb2.ItemResponse()


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    demo_pb2_grpc.add_DemoServiceServicer_to_server(DemoServiceServicer(), server)

    service_names = (
        demo_pb2.DESCRIPTOR.services_by_name["DemoService"].full_name,
        reflection.SERVICE_NAME,
    )
    reflection.enable_server_reflection(service_names, server)

    server.add_insecure_port("[::]:50051")
    logger.info("Server starting on port 50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()