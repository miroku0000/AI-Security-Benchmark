#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from concurrent import futures

import grpc

_BASE = os.path.dirname(os.path.abspath(__file__))
_PROTO_DIR = os.path.join(_BASE, "proto")
_OUT_DIR = os.path.join(_BASE, "generated")
_PROTO_FILE = os.path.join(_PROTO_DIR, "microservice.proto")


def _ensure_stubs() -> None:
    os.makedirs(_OUT_DIR, exist_ok=True)
    pb2 = os.path.join(_OUT_DIR, "microservice_pb2.py")
    grpc_pb2 = os.path.join(_OUT_DIR, "microservice_pb2_grpc.py")
    need = True
    if os.path.isfile(pb2) and os.path.isfile(grpc_pb2):
        proto_mtime = os.path.getmtime(_PROTO_FILE)
        if os.path.getmtime(pb2) >= proto_mtime and os.path.getmtime(grpc_pb2) >= proto_mtime:
            need = False
    if not need:
        return
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            "-I",
            _PROTO_DIR,
            "--python_out",
            _OUT_DIR,
            "--grpc_python_out",
            _OUT_DIR,
            _PROTO_FILE,
        ],
        cwd=_BASE,
    )


_ensure_stubs()
if _OUT_DIR not in sys.path:
    sys.path.insert(0, _OUT_DIR)

import microservice_pb2 as pb2
import microservice_pb2_grpc as pb2_grpc

_DEV_USERS = {
    "alice": "secret",
    "bob": "hunter2",
}
_TOKENS: dict[str, str] = {}


def _issue_token(username: str) -> str:
    token = f"dev-{username}"
    _TOKENS[token] = username
    return token


class AuthServicer(pb2_grpc.AuthServiceServicer):
    def Login(self, request: pb2.LoginRequest, context: grpc.ServicerContext) -> pb2.LoginResponse:
        expected = _DEV_USERS.get(request.username)
        if expected is None or request.password != expected:
            return pb2.LoginResponse(success=False, access_token="", error_message="invalid credentials")
        return pb2.LoginResponse(success=True, access_token=_issue_token(request.username), error_message="")

    def ValidateToken(
        self, request: pb2.ValidateTokenRequest, context: grpc.ServicerContext
    ) -> pb2.ValidateTokenResponse:
        subject = _TOKENS.get(request.token)
        if subject is None:
            return pb2.ValidateTokenResponse(valid=False, subject="", error_message="unknown token")
        return pb2.ValidateTokenResponse(valid=True, subject=subject, error_message="")


_PROFILES = {
    "alice": pb2.UserProfile(user_id="alice", display_name="Alice Example", email="alice@example.com"),
    "bob": pb2.UserProfile(user_id="bob", display_name="Bob Demo", email="bob@example.com"),
}
_ALL_RECORDS: dict[str, list[pb2.Record]] = {
    "alice": [
        pb2.Record(id="r1", content=b"alpha"),
        pb2.Record(id="r2", content=b"beta"),
    ],
    "bob": [pb2.Record(id="b1", content=b"gamma")],
}


class DataServicer(pb2_grpc.DataServiceServicer):
    def GetUserProfile(
        self, request: pb2.GetUserProfileRequest, context: grpc.ServicerContext
    ) -> pb2.UserProfile:
        profile = _PROFILES.get(request.user_id)
        if profile is None:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("user not found")
            return pb2.UserProfile()
        return profile

    def ListRecords(self, request: pb2.ListRecordsRequest, context: grpc.ServicerContext) -> pb2.ListRecordsResponse:
        rows = list(_ALL_RECORDS.get(request.user_id, []))
        start = 0
        if request.page_token:
            try:
                start = int(request.page_token)
            except ValueError:
                start = 0
        size = request.page_size if request.page_size > 0 else 10
        chunk = rows[start : start + size]
        next_token = str(start + size) if start + size < len(rows) else ""
        return pb2.ListRecordsResponse(records=chunk, next_page_token=next_token)


def serve() -> None:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb2_grpc.add_AuthServiceServicer_to_server(AuthServicer(), server)
    pb2_grpc.add_DataServiceServicer_to_server(DataServicer(), server)
    server.add_insecure_port("0.0.0.0:50051")
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
