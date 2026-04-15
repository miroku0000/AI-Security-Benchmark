package com.dataproc.grpc;

import com.dataproc.grpc.v1.DataChunk;
import com.dataproc.grpc.v1.DataTransferServiceGrpc;
import com.dataproc.grpc.v1.DownloadRequest;
import com.dataproc.grpc.v1.StreamEnvelope;
import com.dataproc.grpc.v1.StreamReply;
import com.dataproc.grpc.v1.UploadAck;
import com.dataproc.grpc.v1.UploadChunk;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import com.google.protobuf.ByteString;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public final class DataTransferServiceImpl extends DataTransferServiceGrpc.DataTransferServiceImplBase {

    private static final int DEFAULT_DOWNLOAD_CHUNK = 256 * 1024;

    private final Path storageRoot;

    private final Map<String, Path> resourceIndex = new ConcurrentHashMap<>();

    public DataTransferServiceImpl(Path storageRoot) {
        this.storageRoot = storageRoot;
    }

    @Override
    public StreamObserver<UploadChunk> uploadFile(StreamObserver<UploadAck> responseObserver) {
        return new StreamObserver<>() {
            private String sessionId;
            private Path target;
            private FileChannel channel;
            private long received;

            @Override
            public void onNext(UploadChunk chunk) {
                try {
                    if (sessionId == null) {
                        sessionId = chunk.getSessionId().isEmpty()
                                ? UUID.randomUUID().toString()
                                : chunk.getSessionId();
                        String name = chunk.getMetadataMap().getOrDefault("filename", sessionId);
                        String safe = name.replaceAll("[^a-zA-Z0-9._-]", "_");
                        target = storageRoot.resolve(sessionId + "_" + safe);
                        Files.createDirectories(storageRoot);
                        channel = FileChannel.open(
                                target,
                                StandardOpenOption.CREATE,
                                StandardOpenOption.TRUNCATE_EXISTING,
                                StandardOpenOption.WRITE);
                    }
                    if (!sessionId.equals(chunk.getSessionId()) && !chunk.getSessionId().isEmpty()) {
                        throw new IllegalStateException("session_id mismatch");
                    }
                    if (!chunk.getPayload().isEmpty()) {
                        ByteBuffer buf = chunk.getPayload().asReadOnlyByteBuffer();
                        while (buf.hasRemaining()) {
                            received += channel.write(buf);
                        }
                    }
                    if (chunk.getLast()) {
                        channel.close();
                        channel = null;
                        String resourceId = sessionId;
                        resourceIndex.put(resourceId, target);
                        responseObserver.onNext(UploadAck.newBuilder()
                                .setSessionId(sessionId)
                                .setBytesReceived(received)
                                .setResourceId(resourceId)
                                .setMessage("ok")
                                .build());
                        responseObserver.onCompleted();
                    }
                } catch (Exception e) {
                    cleanup();
                    responseObserver.onError(Status.INTERNAL.withCause(e).withDescription(e.getMessage()).asRuntimeException());
                }
            }

            @Override
            public void onError(Throwable t) {
                cleanup();
            }

            @Override
            public void onCompleted() {
                if (channel != null) {
                    try {
                        channel.close();
                    } catch (IOException ignored) {
                    }
                    channel = null;
                }
            }

            private void cleanup() {
                if (channel != null) {
                    try {
                        channel.close();
                    } catch (IOException ignored) {
                    }
                    channel = null;
                }
                if (target != null) {
                    try {
                        Files.deleteIfExists(target);
                    } catch (IOException ignored) {
                    }
                }
            }
        };
    }

    @Override
    public void downloadResource(DownloadRequest request, StreamObserver<DataChunk> responseObserver) {
        Path path = resourceIndex.get(request.getResourceId());
        if (path == null || !Files.isRegularFile(path)) {
            responseObserver.onError(Status.NOT_FOUND.withDescription("unknown resource").asRuntimeException());
            return;
        }
        int hint = request.getChunkSizeHint();
        int chunkSize = hint > 0 ? Math.min(hint, 16 * 1024 * 1024) : DEFAULT_DOWNLOAD_CHUNK;
        long offset = Math.max(0L, request.getOffset());
        try (FileChannel ch = FileChannel.open(path, StandardOpenOption.READ)) {
            long size = ch.size();
            long pos = offset;
            if (pos >= size) {
                responseObserver.onNext(DataChunk.newBuilder()
                        .setOffset(pos)
                        .setLast(true)
                        .build());
                responseObserver.onCompleted();
                return;
            }
            ch.position(pos);
            ByteBuffer buf = ByteBuffer.allocate(chunkSize);
            while (pos < size) {
                buf.clear();
                int n = ch.read(buf);
                if (n <= 0) {
                    break;
                }
                buf.flip();
                long next = pos + n;
                boolean last = next >= size;
                responseObserver.onNext(DataChunk.newBuilder()
                        .setPayload(ByteString.copyFrom(buf))
                        .setOffset(pos)
                        .setLast(last)
                        .build());
                pos = next;
            }
            responseObserver.onCompleted();
        } catch (IOException e) {
            responseObserver.onError(Status.INTERNAL.withCause(e).asRuntimeException());
        }
    }

    @Override
    public StreamObserver<StreamEnvelope> bidirectionalTransfer(StreamObserver<StreamReply> responseObserver) {
        return new StreamObserver<>() {
            @Override
            public void onNext(StreamEnvelope envelope) {
                StreamReply.Builder b = StreamReply.newBuilder()
                        .setCorrelationId(envelope.getCorrelationId())
                        .putAllHeaders(envelope.getHeadersMap());
                if (!envelope.getPayload().isEmpty()) {
                    b.setPayload(envelope.getPayload());
                }
                responseObserver.onNext(b.build());
                if (envelope.getEndOfMessage()) {
                    responseObserver.onNext(StreamReply.newBuilder()
                            .setCorrelationId(envelope.getCorrelationId())
                            .putHeaders("eos", "true")
                            .build());
                }
            }

            @Override
            public void onError(Throwable t) {
            }

            @Override
            public void onCompleted() {
                responseObserver.onCompleted();
            }
        };
    }
}
