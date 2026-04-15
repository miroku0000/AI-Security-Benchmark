from __future__ import annotations

import os
import subprocess
import sys
from concurrent import futures
from pathlib import Path

import grpc

_ROOT = Path(__file__).resolve().parent
_PROTO = _ROOT / "proto" / "forward.proto"
_PB2 = _ROOT / "forward_pb2.py"
_PB2_GRPC = _ROOT / "forward_pb2_grpc.py"


def _ensure_stubs() -> None:
    if _PB2.is_file() and _PB2_GRPC.is_file():
        return
    cmd = [
        sys.executable,
        "-m",
        "grpc_tools.protoc",
        "-I",
        str(_ROOT / "proto"),
        "--python_out",
        str(_ROOT),
        "--grpc_python_out",
        str(_ROOT),
        str(_PROTO),
    ]
    subprocess.run(cmd, check=True)


_ensure_stubs()

import forward_pb2  # noqa: E402
import forward_pb2_grpc  # noqa: E402


class ForwardService(forward_pb2_grpc.ForwardServiceServicer):
    def Forward(self, request: forward_pb2.ForwardRequest, context: grpc.ServicerContext) -> forward_pb2.ForwardResponse:
        md = {k.lower(): v for k, v in context.invocation_metadata()}
        trailers: list[tuple[str, str]] = []
        for k, v in md.items():
            if k.startswith("x-forwarded-") or k in ("authorization", "x-request-id", "x-correlation-id"):
                trailers.append((f"x-upstream-{k}", v))
        context.set_trailing_metadata(trailers)
        return forward_pb2.ForwardResponse(body=request.body)


def serve() -> None:
    addr = os.environ.get("GRPC_LISTEN", "[::]:50051")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    forward_pb2_grpc.add_ForwardServiceServicer_to_server(ForwardService(), server)
    server.add_insecure_port(addr)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
