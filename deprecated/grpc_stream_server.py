import asyncio
import logging
import time
from concurrent import futures

import grpc
from grpc import aio

# Proto would normally be compiled; inline the servicer pattern here.
# Assumes proto defines: DataStreamService with RPCs:
#   ProcessStream (stream DataRequest) returns (stream DataResponse)
#   IngestStream (stream DataRequest) returns (DataSummary)
#   BroadcastStream (DataRequest) returns (stream DataResponse)

import data_stream_pb2
import data_stream_pb2_grpc

logger = logging.getLogger(__name__)

MAX_MESSAGE_SIZE = 64 * 1024 * 1024  # 64 MB - generous but bounded
MAX_CONCURRENT_STREAMS = 1000
MAX_WORKERS = 16
KEEPALIVE_TIME_MS = 30000
KEEPALIVE_TIMEOUT_MS = 10000


class DataStreamServicer(data_stream_pb2_grpc.DataStreamServiceServicer):

    async def ProcessStream(self, request_iterator, context):
        """Bidirectional streaming RPC for real-time data processing."""
        async for request in request_iterator:
            result = await self._process_data(request)
            yield data_stream_pb2.DataResponse(
                request_id=request.request_id,
                processed_data=result,
                timestamp_ns=time.time_ns(),
            )

    async def IngestStream(self, request_iterator, context):
        """Client streaming RPC for bulk data ingestion."""
        count = 0
        total_bytes = 0
        async for request in request_iterator:
            await self._ingest_data(request)
            count += 1
            total_bytes += len(request.payload)
        return data_stream_pb2.DataSummary(
            records_processed=count,
            total_bytes=total_bytes,
            completed_at_ns=time.time_ns(),
        )

    async def BroadcastStream(self, request, context):
        """Server streaming RPC for pushing processed results."""
        chunks = await self._split_and_process(request)
        for chunk in chunks:
            if context.cancelled():
                return
            yield data_stream_pb2.DataResponse(
                request_id=request.request_id,
                processed_data=chunk,
                timestamp_ns=time.time_ns(),
            )

    async def _process_data(self, request):
        # Placeholder: replace with actual processing logic
        return request.payload

    async def _ingest_data(self, request):
        # Placeholder: replace with actual ingestion logic
        await asyncio.sleep(0)

    async def _split_and_process(self, request):
        # Placeholder: replace with actual chunking/processing
        return [request.payload]


async def serve():
    server = aio.server(
        futures.ThreadPoolExecutor(max_workers=MAX_WORKERS),
        options=[
            ("grpc.max_send_message_length", MAX_MESSAGE_SIZE),
            ("grpc.max_receive_message_length", MAX_MESSAGE_SIZE),
            ("grpc.max_concurrent_streams", MAX_CONCURRENT_STREAMS),
            ("grpc.keepalive_time_ms", KEEPALIVE_TIME_MS),
            ("grpc.keepalive_timeout_ms", KEEPALIVE_TIMEOUT_MS),
            ("grpc.keepalive_permit_without_calls", 1),
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.min_ping_interval_without_data_ms", 5000),
            ("grpc.so_reuseport", 1),
        ],
    )
    data_stream_pb2_grpc.add_DataStreamServiceServicer_to_server(
        DataStreamServicer(), server
    )
    server.add_insecure_port("[::]:50051")
    logger.info("Starting gRPC server on port 50051")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
