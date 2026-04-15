#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import threading
from concurrent import futures
from typing import Callable, Mapping, Optional

import grpc

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _ensure_generated() -> None:
    if os.path.isfile(os.path.join(_ROOT, "ext_authz_pb2.py")):
        return
    try:
        from grpc_tools import protoc
    except ImportError as exc:
        raise RuntimeError(
            "Run: pip install grpcio grpcio-tools && python -m grpc_tools.protoc "
            "-I%s --python_out=%s --grpc_python_out=%s %s"
            % (_ROOT, _ROOT, _ROOT, os.path.join(_ROOT, "ext_authz.proto"))
        ) from exc
    if protoc.main(
        [
            "grpc_tools.protoc",
            "-I" + _ROOT,
            "--python_out=" + _ROOT,
            "--grpc_python_out=" + _ROOT,
            os.path.join(_ROOT, "ext_authz.proto"),
        ]
    ):
        raise RuntimeError("grpc_tools.protoc failed")


_ensure_generated()

import ext_authz_pb2  # noqa: E402
import ext_authz_pb2_grpc  # noqa: E402

INVALID_ARGUMENT = 3
PERMISSION_DENIED = 7
UNAUTHENTICATED = 16


def _lower_headers(h: Mapping[str, str]) -> dict[str, str]:
    return {k.lower(): v for k, v in h.items()}


class EnvoyExtAuthzServicer(ext_authz_pb2_grpc.AuthorizationServicer):
    def __init__(
        self,
        *,
        authorize: Optional[
            Callable[[Mapping[str, str]], tuple[bool, Mapping[str, str], int, str]]
        ] = None,
    ) -> None:
        self._authorize = authorize or self._default_authorize

    @staticmethod
    def _default_authorize(
        headers: Mapping[str, str],
    ) -> tuple[bool, Mapping[str, str], int, str]:
        h = _lower_headers(headers)
        token = h.get("x-custom-auth-token", "").strip()
        if not token:
            return False, {}, UNAUTHENTICATED, "missing x-custom-auth-token"
        if token != os.environ.get("EXPECTED_AUTH_TOKEN", "valid-token"):
            return False, {}, PERMISSION_DENIED, "invalid x-custom-auth-token"
        uid = h.get("x-custom-user-id", "").strip() or "anonymous"
        return True, {"x-auth-user": uid, "x-auth-source": "ext_authz"}, 0, ""

    def Check(
        self,
        request: ext_authz_pb2.CheckRequest,
        context: grpc.ServicerContext,
    ) -> ext_authz_pb2.CheckResponse:
        if not request.HasField("attributes"):
            return self._deny(INVALID_ARGUMENT, "missing attributes")
        req = request.attributes.request
        headers = dict(req.headers)

        allowed, extra_headers, grpc_code, msg = self._authorize(headers)
        if not allowed:
            return self._deny(grpc_code or PERMISSION_DENIED, msg or "denied")

        ok = ext_authz_pb2.OkHttpResponse()
        for key, value in extra_headers.items():
            ok.headers.append(
                ext_authz_pb2.HeaderValueOption(
                    header=ext_authz_pb2.HeaderValue(key=key, value=value),
                    append=False,
                )
            )

        return ext_authz_pb2.CheckResponse(ok_response=ok)

    @staticmethod
    def _deny(grpc_code: int, message: str) -> ext_authz_pb2.CheckResponse:
        st = ext_authz_pb2.Status(code=grpc_code, message=message)
        return ext_authz_pb2.CheckResponse(denied_response=st)


def serve() -> None:
    bind = os.environ.get("EXT_AUTHZ_BIND", "[::]:9000")
    max_workers = int(os.environ.get("EXT_AUTHZ_WORKERS", "8"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    ext_authz_pb2_grpc.add_AuthorizationServicer_to_server(EnvoyExtAuthzServicer(), server)
    if bind.startswith("unix:"):
        path = bind[5:]
        if not server.add_insecure_port("unix:" + path):
            raise RuntimeError("failed to bind unix:%s" % (path,))
    else:
        if server.add_insecure_port(bind) == 0:
            raise RuntimeError("failed to bind %r" % (bind,))
    server.start()
    print("ext_authz listening on %s" % (bind,), flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    serve()
