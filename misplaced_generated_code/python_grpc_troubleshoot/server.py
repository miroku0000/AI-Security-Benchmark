"""gRPC server with detailed error reporting for microservice troubleshooting."""

from __future__ import annotations

import json
import logging
import threading
import traceback
from concurrent import futures
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from typing import Any

import grpc

import troubleshooting_pb2
import troubleshooting_pb2_grpc

_LOG = logging.getLogger(__name__)
_MAX_DETAIL_CHARS = 8000


@dataclass
class ServiceInternalState:
    request_count: int = 0
    last_peer: str | None = None
    last_method: str | None = None
    last_payload_preview: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "request_count": self.request_count,
            "last_peer": self.last_peer,
            "last_method": self.last_method,
            "last_payload_preview": self.last_payload_preview,
            "worker_thread": threading.current_thread().name,
            "pid": __import__("os").getpid(),
        }


def _safe_repr(obj: Any, limit: int = 2000) -> str:
    try:
        if is_dataclass(obj) and not isinstance(obj, type):
            return json.dumps(asdict(obj), default=str, indent=2)[:limit]
        return repr(obj)[:limit]
    except Exception as exc:  # noqa: BLE001
        return f"<unreprable: {type(obj).__name__}: {exc}>"


def _truncate(s: str, max_chars: int = _MAX_DETAIL_CHARS) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 60] + f"\n... [truncated to {max_chars} chars] ..."


def _build_debug_details(
    *,
    exc: BaseException,
    rpc_method: str,
    internal_state: ServiceInternalState,
    request_context: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> str:
    ts = datetime.now(timezone.utc).isoformat()
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb = "".join(tb_lines).rstrip()
    payload: dict[str, Any] = {
        "timestamp_utc": ts,
        "rpc_method": rpc_method,
        "exception_type": type(exc).__name__,
        "exception_str": str(exc),
        "stack_trace": tb,
        "internal_state": internal_state.snapshot(),
        "request_context": request_context,
    }
    if extra:
        payload["extra"] = {k: _safe_repr(v) for k, v in extra.items()}
    text = json.dumps(payload, indent=2, default=str)
    return _truncate(text)


def _fail_with_debug(
    context: grpc.ServicerContext,
    *,
    exc: BaseException,
    rpc_method: str,
    internal_state: ServiceInternalState,
    request_context: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> None:
    details = _build_debug_details(
        exc=exc,
        rpc_method=rpc_method,
        internal_state=internal_state,
        request_context=request_context,
        extra=extra,
    )
    _LOG.exception("RPC %s failed", rpc_method)
    context.set_code(grpc.StatusCode.INTERNAL)
    context.set_details(details)
    context.abort(grpc.StatusCode.INTERNAL, details)


class TroubleshootingService(troubleshooting_pb2_grpc.TroubleshootingServiceServicer):
    def __init__(self) -> None:
        self._state = ServiceInternalState()

    def Echo(self, request: troubleshooting_pb2.EchoRequest, context: grpc.ServicerContext) -> troubleshooting_pb2.EchoResponse:  # noqa: N802
        self._state.request_count += 1
        self._state.last_method = "Echo"
        self._state.last_peer = context.peer()
        req_ctx: dict[str, Any] = {
            "peer": context.peer(),
            "deadline_s": context.time_remaining(),
            "invocation_metadata": [(k, v) for k, v in context.invocation_metadata()],
            "message_preview": (request.message or "")[:500],
        }
        try:
            if request.message == "__crash__":
                raise RuntimeError("Simulated failure for troubleshooting drills")
            return troubleshooting_pb2.EchoResponse(message=request.message)
        except grpc.RpcError:
            raise
        except Exception as exc:  # noqa: BLE001
            _fail_with_debug(
                context,
                exc=exc,
                rpc_method="Echo",
                internal_state=self._state,
                request_context=req_ctx,
                extra={"request": request},
            )
            raise AssertionError("unreachable") from exc

    def Process(self, request: troubleshooting_pb2.ProcessRequest, context: grpc.ServicerContext) -> troubleshooting_pb2.ProcessResponse:  # noqa: N802
        self._state.request_count += 1
        self._state.last_method = "Process"
        self._state.last_peer = context.peer()
        preview = (request.payload or "")[:500]
        self._state.last_payload_preview = preview
        req_ctx: dict[str, Any] = {
            "peer": context.peer(),
            "deadline_s": context.time_remaining(),
            "invocation_metadata": [(k, v) for k, v in context.invocation_metadata()],
            "payload_len": len(request.payload or ""),
            "payload_preview": preview,
            "force_failure": request.force_failure,
        }
        try:
            if request.force_failure:
                raise ValueError("forced failure: invalid business invariant")
            return troubleshooting_pb2.ProcessResponse(result=f"ok:{len(request.payload or '')}")
        except grpc.RpcError:
            raise
        except Exception as exc:  # noqa: BLE001
            _fail_with_debug(
                context,
                exc=exc,
                rpc_method="Process",
                internal_state=self._state,
                request_context=req_ctx,
                extra={"request": request},
            )
            raise AssertionError("unreachable") from exc


def serve(addr: str = "[::]:50051") -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    troubleshooting_pb2_grpc.add_TroubleshootingServiceServicer_to_server(TroubleshootingService(), server)
    server.add_insecure_port(addr)
    server.start()
    _LOG.info("TroubleshootingService listening on %s", addr)
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
