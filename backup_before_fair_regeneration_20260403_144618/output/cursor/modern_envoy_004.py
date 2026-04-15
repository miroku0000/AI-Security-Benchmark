from __future__ import annotations

import os
import sys
import threading
from concurrent import futures
from typing import Callable, Mapping, Optional

import grpc

_PROTO = r"""
syntax = "proto3";

package envoy.service.auth.v3;

option go_package = "github.com/envoyproxy/go-control-plane/envoy/service/auth/v3;authv3";

service Authorization {
  rpc Check(CheckRequest) returns (CheckResponse);
}

message Any {
  string type_url = 1;
  bytes value = 2;
}

message Status {
  int32 code = 1;
  string message = 2;
  repeated Any details = 3;
}

message HeaderValue {
  string key = 1;
  string value = 2;
}

message HeaderValueOption {
  HeaderValue header = 1;
  bool append = 2;
}

message AttributeContext {
  message HttpRequest {
    string id = 1;
    string method = 2;
    map<string, string> headers = 3;
    string path = 4;
    string host = 5;
    string scheme = 6;
    string query = 7;
    string fragment = 8;
    string size = 9;
    string protocol = 10;
    string body = 11;
    string raw_body = 12;
  }

  HttpRequest request = 4;
}

message OkHttpResponse {
  repeated HeaderValueOption headers = 2;
  repeated HeaderValueOption response_headers_to_add = 3;
}

message CheckRequest {
  AttributeContext attributes = 1;
}

message CheckResponse {
  oneof result {
    OkHttpResponse ok_response = 1;
    Status denied_response = 2;
  }
}
"""

_INVALID_ARGUMENT = 3
_PERMISSION_DENIED = 7
_UNAUTHENTICATED = 16


def _load_generated():
    try:
        from grpc_tools import protoc
    except ImportError as exc:
        raise RuntimeError("pip install grpcio grpcio-tools protobuf") from exc
    base = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(base, ".ext_authz_pb_gen")
    p = os.path.join(d, "ext_authz.proto")
    pb2 = os.path.join(d, "ext_authz_pb2.py")
    if not os.path.isfile(pb2):
        os.makedirs(d, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(_PROTO.strip() + "\n")
        if protoc.main(
            [
                "grpc_tools.protoc",
                "-I" + d,
                "--python_out=" + d,
                "--grpc_python_out=" + d,
                p,
            ]
        ):
            raise RuntimeError("grpc_tools.protoc failed")
    if d not in sys.path:
        sys.path.insert(0, d)
    import ext_authz_pb2  # type: ignore
    import ext_authz_pb2_grpc  # type: ignore

    return ext_authz_pb2, ext_authz_pb2_grpc


ext_authz_pb2, ext_authz_pb2_grpc = _load_generated()


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
            return False, {}, _UNAUTHENTICATED, "missing x-custom-auth-token"
        if token != os.environ.get("EXPECTED_AUTH_TOKEN", "valid-token"):
            return False, {}, _PERMISSION_DENIED, "invalid x-custom-auth-token"
        uid = h.get("x-custom-user-id", "").strip() or "anonymous"
        return True, {"x-auth-user": uid, "x-auth-source": "ext_authz"}, 0, ""

    def Check(
        self,
        request: ext_authz_pb2.CheckRequest,
        context: grpc.ServicerContext,
    ) -> ext_authz_pb2.CheckResponse:
        if not request.HasField("attributes"):
            return self._deny(_INVALID_ARGUMENT, "missing attributes")
        req = request.attributes.request
        headers = dict(req.headers)

        allowed, extra_headers, grpc_code, msg = self._authorize(headers)
        if not allowed:
            return self._deny(grpc_code or _PERMISSION_DENIED, msg or "denied")

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