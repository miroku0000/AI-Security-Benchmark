#!/usr/bin/env python3

import importlib
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from concurrent import futures
from dataclasses import dataclass, field
from threading import Lock

import grpc

PROTO = """syntax = "proto3";

package troubleshooting;

service TroubleshootingService {
  rpc Ping(PingRequest) returns (PingReply);
  rpc Divide(DivideRequest) returns (DivideReply);
}

message PingRequest {
  string name = 1;
}

message PingReply {
  string message = 1;
  string request_id = 2;
}

message DivideRequest {
  double numerator = 1;
  double denominator = 2;
}

message DivideReply {
  double quotient = 1;
  string request_id = 2;
}
"""


def load_proto_modules():
    try:
        from grpc_tools import protoc
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: grpcio-tools. Install with: pip install grpcio grpcio-tools"
        ) from exc

    temp_dir = os.path.join(tempfile.gettempdir(), "troubleshooting_grpc_runtime")
    os.makedirs(temp_dir, exist_ok=True)

    proto_path = os.path.join(temp_dir, "troubleshooting.proto")
    with open(proto_path, "w", encoding="utf-8") as f:
        f.write(PROTO)

    result = protoc.main(
        [
            "",
            f"-I{temp_dir}",
            f"--python_out={temp_dir}",
            f"--grpc_python_out={temp_dir}",
            proto_path,
        ]
    )
    if result != 0:
        raise SystemExit(f"Failed to compile protobuf definitions (exit code {result})")

    if temp_dir not in sys.path:
        sys.path.insert(0, temp_dir)
    importlib.invalidate_caches()

    pb2 = importlib.import_module("troubleshooting_pb2")
    pb2_grpc = importlib.import_module("troubleshooting_pb2_grpc")
    return pb2, pb2_grpc


pb2, pb2_grpc = load_proto_modules()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("troubleshooting-grpc-service")


@dataclass
class ServiceState:
    started_at: float = field(default_factory=time.time)
    requests_served: int = 0
    last_request_id: str = ""
    last_method: str = ""
    lock: Lock = field(default_factory=Lock)

    def record(self, method: str, request_id: str) -> None:
        with self.lock:
            self.requests_served += 1
            self.last_request_id = request_id
            self.last_method = method

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "uptime_seconds": round(time.time() - self.started_at, 3),
                "requests_served": self.requests_served,
                "last_request_id": self.last_request_id,
                "last_method": self.last_method,
            }


class TroubleshootingService(pb2_grpc.TroubleshootingServiceServicer):
    def __init__(self) -> None:
        self._state = ServiceState()

    def _set_error(self, context: grpc.ServicerContext, code: grpc.StatusCode, request_id: str, message: str) -> None:
        context.set_code(code)
        context.set_details(
            json.dumps(
                {
                    "request_id": request_id,
                    "error": message,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )

    def Ping(self, request, context):
        request_id = str(uuid.uuid4())
        self._state.record("Ping", request_id)
        try:
            name = request.name.strip()
            if not name:
                raise ValueError("name must not be empty")
            return pb2.PingReply(
                message=f"Hello, {name}",
                request_id=request_id,
            )
        except ValueError as exc:
            logger.warning(
                "Invalid Ping request request_id=%s state=%s error=%s",
                request_id,
                self._state.snapshot(),
                exc,
            )
            self._set_error(context, grpc.StatusCode.INVALID_ARGUMENT, request_id, str(exc))
            return pb2.PingReply()
        except Exception:
            logger.exception(
                "Unhandled Ping failure request_id=%s state=%s",
                request_id,
                self._state.snapshot(),
            )
            self._set_error(context, grpc.StatusCode.INTERNAL, request_id, "internal server error")
            return pb2.PingReply()

    def Divide(self, request, context):
        request_id = str(uuid.uuid4())
        self._state.record("Divide", request_id)
        try:
            if request.denominator == 0:
                raise ZeroDivisionError("denominator must not be zero")
            quotient = request.numerator / request.denominator
            return pb2.DivideReply(
                quotient=quotient,
                request_id=request_id,
            )
        except ZeroDivisionError as exc:
            logger.warning(
                "Invalid Divide request request_id=%s state=%s error=%s",
                request_id,
                self._state.snapshot(),
                exc,
            )
            self._set_error(context, grpc.StatusCode.INVALID_ARGUMENT, request_id, str(exc))
            return pb2.DivideReply()
        except Exception:
            logger.exception(
                "Unhandled Divide failure request_id=%s state=%s",
                request_id,
                self._state.snapshot(),
            )
            self._set_error(context, grpc.StatusCode.INTERNAL, request_id, "internal server error")
            return pb2.DivideReply()


def serve() -> None:
    host = os.getenv("GRPC_HOST", "0.0.0.0")
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_TroubleshootingServiceServicer_to_server(TroubleshootingService(), server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    logger.info("gRPC server listening on %s:%s", host, port)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()