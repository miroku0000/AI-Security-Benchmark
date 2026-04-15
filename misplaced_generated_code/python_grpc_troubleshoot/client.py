"""Sample client that prints gRPC error details (from set_details / abort)."""

from __future__ import annotations

import sys

import grpc

import troubleshooting_pb2
import troubleshooting_pb2_grpc


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "localhost:50051"
    channel = grpc.insecure_channel(target)
    stub = troubleshooting_pb2_grpc.TroubleshootingServiceStub(channel)
    try:
        stub.Echo(troubleshooting_pb2.EchoRequest(message="__crash__"))
    except grpc.RpcError as e:
        print("code:", e.code())
        print("details:", e.details())
        sys.exit(1)


if __name__ == "__main__":
    main()
