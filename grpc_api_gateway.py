#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from concurrent import futures
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Iterable, List, Tuple, Union

import grpc
from google.protobuf import descriptor_pb2
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import GetMessageClass

_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "content-length",
        "host",
    }
)


def _build_descriptor_pool() -> DescriptorPool:
    fd = descriptor_pb2.FileDescriptorProto()
    fd.name = "gateway.proto"
    fd.package = "gateway.v1"
    fd.syntax = "proto3"

    fr = fd.message_type.add()
    fr.name = "ForwardRequest"
    f = fr.field.add()
    f.name = "path"
    f.number = 1
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    f = fr.field.add()
    f.name = "body"
    f.number = 2
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES

    fp = fd.message_type.add()
    fp.name = "ForwardResponse"
    f = fp.field.add()
    f.name = "body"
    f.number = 1
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
    f = fp.field.add()
    f.name = "status"
    f.number = 2
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT32

    svc = fd.service.add()
    svc.name = "ForwardService"
    m = svc.method.add()
    m.name = "Forward"
    m.input_type = ".gateway.v1.ForwardRequest"
    m.output_type = ".gateway.v1.ForwardResponse"

    pool = DescriptorPool()
    pool.AddSerializedFile(fd.SerializeToString())
    return pool


_POOL = _build_descriptor_pool()
_ForwardRequest = GetMessageClass(_POOL.FindMessageTypeByName("gateway.v1.ForwardRequest"))
_ForwardResponse = GetMessageClass(_POOL.FindMessageTypeByName("gateway.v1.ForwardResponse"))
_FORWARD_METHOD = "/gateway.v1.ForwardService/Forward"


def _grpc_safe_header_value(value: str) -> str:
    return value.replace("\r", "").replace("\n", " ")


def build_metadata_from_headers(
    headers: Iterable[Tuple[str, Union[str, bytes]]],
) -> List[Tuple[str, Union[str, bytes]]]:
    out: List[Tuple[str, Union[str, bytes]]] = []
    for name, value in headers:
        key = name.lower()
        if key in _HOP_BY_HOP:
            continue
        if isinstance(value, bytes):
            out.append((key, value))
        else:
            out.append((key, _grpc_safe_header_value(value)))
    return out


def _add_forward_service(
    server: grpc.Server,
    forward_fn,
) -> None:
    rpc_method_handlers = {
        "Forward": grpc.unary_unary_rpc_method_handler(
            forward_fn,
            request_deserializer=_ForwardRequest.FromString,
            response_serializer=_ForwardResponse.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "gateway.v1.ForwardService",
        rpc_method_handlers,
    )
    server.add_generic_rpc_handlers((generic_handler,))


class BackendForwardServicer:
    def Forward(self, request, context):
        trailing: List[Tuple[str, str | bytes]] = []
        for key, value in context.invocation_metadata():
            lk = key.lower()
            if lk.endswith("-bin"):
                trailing.append((lk, value if isinstance(value, bytes) else value.encode("latin1")))
            else:
                if isinstance(value, bytes):
                    value = value.decode("latin1", errors="replace")
                trailing.append((lk, value))
        context.set_trailing_metadata(tuple(trailing))
        return _ForwardResponse(body=request.body, status=200)


class BackendForwardingClient:
    def __init__(self, backend_target: str) -> None:
        self._channel = grpc.insecure_channel(backend_target)
        self._rpc = self._channel.unary_unary(
            _FORWARD_METHOD,
            request_serializer=_ForwardRequest.SerializeToString,
            response_deserializer=_ForwardResponse.FromString,
        )

    def forward_with_call(self, request, metadata: Iterable[Tuple[str, Union[str, bytes]]]):
        return self._rpc.with_call(request, metadata=list(metadata))


class GrpcGatewayServicer:
    def __init__(self, backend_target: str) -> None:
        self._client = BackendForwardingClient(backend_target)

    def Forward(self, request, context):
        md = build_metadata_from_headers((k, v) for k, v in context.invocation_metadata())
        response, call = self._client.forward_with_call(request, md)
        context.set_trailing_metadata(call.trailing_metadata())
        return response


def _run_backend(bind: str, threads: int) -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=threads))
    _add_forward_service(server, BackendForwardServicer().Forward)
    server.add_insecure_port(bind)
    server.start()
    server.wait_for_termination()


def _run_grpc_gateway(grpc_bind: str, backend_target: str, threads: int) -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=threads))
    _add_forward_service(server, GrpcGatewayServicer(backend_target).Forward)
    server.add_insecure_port(grpc_bind)
    server.start()
    server.wait_for_termination()


def _run_http_gateway(http_bind: str, backend_target: str) -> None:
    client = BackendForwardingClient(backend_target)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *args) -> None:
            return

        def _read_body(self) -> bytes:
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            return self.rfile.read(length) if length else b""

        def _forward(self, send_body: bool = True) -> None:
            body = self._read_body()
            req = _ForwardRequest()
            req.path = self.path
            req.body = body
            metadata = build_metadata_from_headers(self.headers.items())
            try:
                response, call = client.forward_with_call(req, metadata)
            except grpc.RpcError as err:
                self.send_error(502, f"gRPC error: {err.code().name}")
                return
            self.send_response(response.status if response.status else 200)
            for key, value in call.trailing_metadata():
                if str(key).lower().startswith("grpc-"):
                    continue
                if key.lower().endswith("-bin"):
                    if isinstance(value, bytes):
                        value = value.decode("latin1", errors="replace")
                self.send_header(key, value)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            if send_body:
                self.wfile.write(response.body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
                return
            self._forward()

        def do_POST(self) -> None:
            self._forward()

        def do_PUT(self) -> None:
            self._forward()

        def do_PATCH(self) -> None:
            self._forward()

        def do_DELETE(self) -> None:
            self._forward()

        def do_HEAD(self) -> None:
            self._forward(send_body=False)

        def do_OPTIONS(self) -> None:
            self._forward()

    host, _, port_s = http_bind.partition(":")
    port = int(port_s or "8080")
    host = host or "0.0.0.0"
    httpd = HTTPServer((host, port), Handler)
    httpd.serve_forever()


def _parse_bind(addr: str, default_port: int) -> str:
    if addr.startswith("["):
        return addr
    if ":" in addr:
        return addr
    return f"{addr}:{default_port}"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--mode",
        choices=("backend", "http-gateway", "grpc-gateway"),
        default=os.environ.get("GATEWAY_MODE", "http-gateway"),
    )
    p.add_argument("--backend", default=os.environ.get("BACKEND_TARGET", "127.0.0.1:50051"))
    p.add_argument("--bind", default=os.environ.get("GRPC_BIND", "127.0.0.1:50051"))
    p.add_argument("--grpc-bind", default=os.environ.get("GRPC_GATEWAY_BIND", "127.0.0.1:50052"))
    p.add_argument("--http", default=os.environ.get("HTTP_BIND", "0.0.0.0:8080"))
    p.add_argument("--threads", type=int, default=max(8, (os.cpu_count() or 2) * 4))
    args = p.parse_args(argv)

    if args.mode == "backend":
        _run_backend(_parse_bind(args.bind, 50051), args.threads)
    elif args.mode == "grpc-gateway":
        _run_grpc_gateway(_parse_bind(args.grpc_bind, 50052), args.backend, args.threads)
    else:
        _run_http_gateway(args.http, args.backend)


if __name__ == "__main__":
    main()
