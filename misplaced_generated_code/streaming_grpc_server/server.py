import argparse
import os
import sys
from concurrent import futures

import grpc
from google.protobuf import descriptor_pb2
from google.protobuf.descriptor_pool import DescriptorPool
from google.protobuf.message_factory import GetMessageClass


def _build_descriptor_pool() -> DescriptorPool:
    fd = descriptor_pb2.FileDescriptorProto()
    fd.name = "streaming.proto"
    fd.package = "streamapi.v1"
    fd.syntax = "proto3"

    sc = fd.message_type.add()
    sc.name = "StreamChunk"
    f = sc.field.add()
    f.name = "payload"
    f.number = 1
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_BYTES
    f = sc.field.add()
    f.name = "seq"
    f.number = 2
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT64

    ps = fd.message_type.add()
    ps.name = "ProcessSummary"
    f = ps.field.add()
    f.name = "chunks_received"
    f.number = 1
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT64
    f = ps.field.add()
    f.name = "bytes_received"
    f.number = 2
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT64

    sr = fd.message_type.add()
    sr.name = "StreamRequest"
    f = sr.field.add()
    f.name = "start_seq"
    f.number = 1
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT64
    f = sr.field.add()
    f.name = "count"
    f.number = 2
    f.label = descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    f.type = descriptor_pb2.FieldDescriptorProto.TYPE_UINT32

    svc = fd.service.add()
    svc.name = "DataStream"
    m = svc.method.add()
    m.name = "ProcessBidirectional"
    m.input_type = ".streamapi.v1.StreamChunk"
    m.output_type = ".streamapi.v1.StreamChunk"
    m.client_streaming = True
    m.server_streaming = True
    m = svc.method.add()
    m.name = "ProcessClientStream"
    m.input_type = ".streamapi.v1.StreamChunk"
    m.output_type = ".streamapi.v1.ProcessSummary"
    m.client_streaming = True
    m.server_streaming = False
    m = svc.method.add()
    m.name = "ProcessServerStream"
    m.input_type = ".streamapi.v1.StreamRequest"
    m.output_type = ".streamapi.v1.StreamChunk"
    m.client_streaming = False
    m.server_streaming = True

    pool = DescriptorPool()
    pool.AddSerializedFile(fd.SerializeToString())
    return pool


_POOL = _build_descriptor_pool()
_StreamChunk = GetMessageClass(_POOL.FindMessageTypeByName("streamapi.v1.StreamChunk"))
_ProcessSummary = GetMessageClass(_POOL.FindMessageTypeByName("streamapi.v1.ProcessSummary"))
_StreamRequest = GetMessageClass(_POOL.FindMessageTypeByName("streamapi.v1.StreamRequest"))


class DataStreamServicer:
    def ProcessBidirectional(self, request_iterator, context):
        for req in request_iterator:
            out = _StreamChunk()
            out.payload = req.payload
            out.seq = req.seq
            yield out

    def ProcessClientStream(self, request_iterator, context):
        summary = _ProcessSummary()
        for req in request_iterator:
            summary.chunks_received += 1
            summary.bytes_received += len(req.payload)
        return summary

    def ProcessServerStream(self, request, context):
        seq = request.start_seq
        n = request.count if request.count else 1
        for _ in range(n):
            chunk = _StreamChunk()
            chunk.seq = seq
            chunk.payload = b""
            seq += 1
            yield chunk


def _add_servicer(servicer, server):
    rpc_method_handlers = {
        "ProcessBidirectional": grpc.stream_stream_rpc_method_handler(
            servicer.ProcessBidirectional,
            request_deserializer=_StreamChunk.FromString,
            response_serializer=_StreamChunk.SerializeToString,
        ),
        "ProcessClientStream": grpc.stream_unary_rpc_method_handler(
            servicer.ProcessClientStream,
            request_deserializer=_StreamChunk.FromString,
            response_serializer=_ProcessSummary.SerializeToString,
        ),
        "ProcessServerStream": grpc.unary_stream_rpc_method_handler(
            servicer.ProcessServerStream,
            request_deserializer=_StreamRequest.FromString,
            response_serializer=_StreamChunk.SerializeToString,
        ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
        "streamapi.v1.DataStream", rpc_method_handlers
    )
    server.add_generic_rpc_handlers((generic_handler,))


def _server_options():
    return (
        ("grpc.max_send_message_length", -1),
        ("grpc.max_receive_message_length", -1),
        ("grpc.max_concurrent_streams", 0),
        ("grpc.http2.max_pings_without_data", 0),
        ("grpc.http2.min_time_between_pings_ms", 10),
        ("grpc.http2.min_ping_interval_without_data_ms", 10),
        ("grpc.keepalive_time_ms", 2147483647),
        ("grpc.keepalive_timeout_ms", 20000),
        ("grpc.keepalive_permit_without_calls", 1),
        ("grpc.http2.max_ping_strikes", 0),
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--bind",
        default=os.environ.get("GRPC_BIND", "[::]:50051"),
        help="host:port",
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=max(32, (os.cpu_count() or 8) * 8),
        help="thread pool workers",
    )
    args = parser.parse_args()

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=args.threads),
        options=list(_server_options()),
        maximum_concurrent_rpcs=None,
    )
    _add_servicer(DataStreamServicer(), server)
    if ":" in args.bind:
        listen_addr = args.bind
    else:
        listen_addr = f"{args.bind}:50051"
    server.add_insecure_port(listen_addr)
    server.start()
    sys.stderr.write(f"gRPC listening on {listen_addr}\n")
    server.wait_for_termination()


if __name__ == "__main__":
    main()
