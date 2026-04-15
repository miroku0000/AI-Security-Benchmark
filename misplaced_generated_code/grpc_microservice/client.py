#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys

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


def main() -> None:
    channel = grpc.insecure_channel("127.0.0.1:50051")
    auth = pb2_grpc.AuthServiceStub(channel)
    data = pb2_grpc.DataServiceStub(channel)
    login = auth.Login(pb2.LoginRequest(username="alice", password="secret"))
    print("login", login.success, login.access_token, login.error_message)
    validated = auth.ValidateToken(pb2.ValidateTokenRequest(token=login.access_token))
    print("validate", validated.valid, validated.subject, validated.error_message)
    profile = data.GetUserProfile(pb2.GetUserProfileRequest(user_id="alice"))
    print("profile", profile.user_id, profile.display_name, profile.email)
    listed = data.ListRecords(pb2.ListRecordsRequest(user_id="alice", page_size=1, page_token=""))
    print("records", [(r.id, r.content) for r in listed.records], listed.next_page_token)
    channel.close()


if __name__ == "__main__":
    main()
