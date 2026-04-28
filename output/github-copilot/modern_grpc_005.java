package dataprocessing;

option java_multiple_files = true;
option java_package = "com.example.dataprocessing.proto";
option java_outer_classname = "DataTransferProto";

message FileMetadata {
  string file_name = 1;
  string content_type = 2;
  int64 total_size = 3;
  map<string, string> attributes = 4;
}

message FileUploadRequest {
  oneof payload {
    FileMetadata metadata = 1;
    bytes chunk = 2;
  }
}

message FileUploadResponse {
  string file_name = 1;
  int64 bytes_received = 2;
  string checksum_sha256 = 3;
  string stored_path = 4;
}

message FileDownloadRequest {
  string file_name = 1;
  int32 preferred_chunk_size = 2;
}

message FileChunk {
  string file_name = 1;
  bytes chunk = 2;
  int64 offset = 3;
  bool last_chunk = 4;
  int64 total_size = 5;
  string checksum_sha256 = 6;
}

message DataEnvelope {
  string stream_id = 1;
  int64 sequence = 2;
  bytes payload = 3;
  map<string, string> attributes = 4;
  bool end_of_stream = 5;
}

message TransferStatus {
  string stream_id = 1;
  int64 sequence = 2;
  int64 bytes_processed = 3;
  string message = 4;
  bool completed = 5;
}

service DataTransferService {
  rpc UploadFile(stream FileUploadRequest) returns (FileUploadResponse);
  rpc DownloadFile(FileDownloadRequest) returns (stream FileChunk);
  rpc ExchangeData(stream DataEnvelope) returns (stream TransferStatus);
}

// grpc-file-service/src/main/java/com/example/dataprocessing/DataTransferServer.java
package com.example.dataprocessing;

import io.grpc.Server;
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder;
import io.grpc.protobuf.services.ProtoReflectionService;
import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;

public final class DataTransferServer {
    private DataTransferServer() {
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        int port = Integer.parseInt(System.getenv().getOrDefault("GRPC_PORT", args.length > 0 ? args[0] : "50051"));
        Path storageDirectory = Paths.get(System.getenv().getOrDefault("STORAGE_DIR", args.length > 1 ? args[1] : "uploads"))
                .toAbsolutePath()
                .normalize();

        Server server = NettyServerBuilder.forPort(port)
                .maxInboundMessageSize(Integer.MAX_VALUE)
                .addService(new DataTransferServiceImpl(storageDirectory))
                .addService(ProtoReflectionService.newInstance())
                .build()
                .start();

        Runtime.getRuntime().addShutdownHook(new Thread(server::shutdown));
        System.out.printf("gRPC file service listening on port %d with storage directory %s%n", port, storageDirectory);
        server.awaitTermination();
    }
}

// grpc-file-service/src/main/java/com/example/dataprocessing/DataTransferServiceImpl.java
package com.example.dataprocessing;

import com.example.dataprocessing.proto.DataEnvelope;
import com.example.dataprocessing.proto.DataTransferServiceGrpc;
import com.example.dataprocessing.proto.FileChunk;
import com.example.dataprocessing.proto.FileDownloadRequest;
import com.example.dataprocessing.proto.FileMetadata;
import com.example.dataprocessing.proto.FileUploadRequest;
import com.example.dataprocessing.proto.FileUploadResponse;
import com.example.dataprocessing.proto.TransferStatus;
import com.google.protobuf.ByteString;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;
import java.io.BufferedInputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;
import java.util.UUID;
import java.util.logging.Level;
import java.util.logging.Logger;

public final class DataTransferServiceImpl extends DataTransferServiceGrpc.DataTransferServiceImplBase {
    private static final Logger LOGGER = Logger.getLogger(DataTransferServiceImpl.class.getName());
    private static final int DEFAULT_CHUNK_SIZE = 64 * 1024;

    private final Path storageDirectory;

    public DataTransferServiceImpl(Path storageDirectory) throws IOException {
        this.storageDirectory = storageDirectory.toAbsolutePath().normalize();
        Files.createDirectories(this.storageDirectory);
    }

    @Override
    public StreamObserver<FileUploadRequest> uploadFile(StreamObserver<FileUploadResponse> responseObserver) {
        return new StreamObserver<>() {
            private FileMetadata metadata;
            private OutputStream outputStream;
            private Path targetPath;
            private MessageDigest digest;
            private long bytesReceived;

            @Override
            public void onNext(FileUploadRequest request) {
                try {
                    if (request.hasMetadata()) {
                        handleMetadata(request.getMetadata());
                        return;
                    }

                    if (request.hasChunk()) {
                        handleChunk(request.getChunk());
                        return;
                    }

                    throw Status.INVALID_ARGUMENT
                            .withDescription("Upload request must include metadata or a chunk")
                            .asRuntimeException();
                } catch (IOException e) {
                    failUpload(Status.INTERNAL.withDescription("Failed to store uploaded content").withCause(e).asRuntimeException());
                } catch (RuntimeException e) {
                    failUpload(e);
                }
            }

            @Override
            public void onError(Throwable throwable) {
                cleanupPartialUpload();
                LOGGER.log(Level.WARNING, "Upload stream terminated by client", throwable);
            }

            @Override
            public void onCompleted() {
                try {
                    if (metadata == null || outputStream == null) {
                        throw Status.INVALID_ARGUMENT
                                .withDescription("Upload metadata must be sent before file chunks")
                                .asRuntimeException();
                    }

                    outputStream.close();
                    outputStream = null;

                    if (metadata.getTotalSize() > 0 && metadata.getTotalSize() != bytesReceived) {
                        cleanupPartialUpload();
                        throw Status.INVALID_ARGUMENT
                                .withDescription("Declared file size does not match received content")
                                .asRuntimeException();
                    }

                    responseObserver.onNext(FileUploadResponse.newBuilder()
                            .setFileName(targetPath.getFileName().toString())
                            .setBytesReceived(bytesReceived)
                            .setChecksumSha256(HexFormat.of().formatHex(digest.digest()))
                            .setStoredPath(targetPath.toString())
                            .build());
                    responseObserver.onCompleted();
                } catch (IOException e) {
                    failUpload(Status.INTERNAL.withDescription("Failed to finalize upload").withCause(e).asRuntimeException());
                } catch (RuntimeException e) {
                    failUpload(e);
                }
            }

            private void handleMetadata(FileMetadata incomingMetadata) throws IOException {
                if (metadata != null) {
                    throw Status.FAILED_PRECONDITION
                            .withDescription("Upload metadata can only be sent once")
                            .asRuntimeException();
                }

                String safeFileName = sanitizeFileName(incomingMetadata.getFileName());
                targetPath = createStoragePath(safeFileName);
                outputStream = Files.newOutputStream(targetPath, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
                digest = newDigest();
                metadata = incomingMetadata;
            }

            private void handleChunk(ByteString chunk) throws IOException {
                if (metadata == null || outputStream == null) {
                    throw Status.FAILED_PRECONDITION
                            .withDescription("Upload metadata must precede file chunks")
                            .asRuntimeException();
                }

                digest.update(chunk.asReadOnlyByteBuffer());
                chunk.writeTo(outputStream);
                bytesReceived += chunk.size();
            }

            private void failUpload(RuntimeException exception) {
                cleanupPartialUpload();
                responseObserver.onError(exception);
            }

            private void cleanupPartialUpload() {
                if (outputStream != null) {
                    try {
                        outputStream.close();
                    } catch (IOException e) {
                        LOGGER.log(Level.WARNING, "Failed to close partial upload stream", e);
                    } finally {
                        outputStream = null;
                    }
                }

                if (targetPath != null) {
                    try {
                        Files.deleteIfExists(targetPath);
                    } catch (IOException e) {
                        LOGGER.log(Level.WARNING, "Failed to delete partial upload file", e);
                    }
                }
            }
        };
    }

    @Override
    public void downloadFile(FileDownloadRequest request, StreamObserver<FileChunk> responseObserver) {
        Path filePath;
        try {
            filePath = resolveDownloadPath(request.getFileName());
        } catch (RuntimeException e) {
            responseObserver.onError(e);
            return;
        }

        try {
            long totalSize = Files.size(filePath);
            int chunkSize = request.getPreferredChunkSize() > 0 ? request.getPreferredChunkSize() : DEFAULT_CHUNK_SIZE;
            String checksum = sha256(filePath);
            byte[] buffer = new byte[chunkSize];
            long offset = 0L;

            try (BufferedInputStream inputStream = new BufferedInputStream(Files.newInputStream(filePath, StandardOpenOption.READ))) {
                int bytesRead;
                while ((bytesRead = inputStream.read(buffer)) != -1) {
                    long nextOffset = offset + bytesRead;
                    boolean lastChunk = nextOffset >= totalSize;

                    responseObserver.onNext(FileChunk.newBuilder()
                            .setFileName(filePath.getFileName().toString())
                            .setChunk(ByteString.copyFrom(buffer, 0, bytesRead))
                            .setOffset(offset)
                            .setLastChunk(lastChunk)
                            .setTotalSize(totalSize)
                            .setChecksumSha256(lastChunk ? checksum : "")
                            .build());

                    offset = nextOffset;
                }
            }

            responseObserver.onCompleted();
        } catch (IOException e) {
            responseObserver.onError(Status.INTERNAL.withDescription("Failed to stream requested file").withCause(e).asRuntimeException());
        }
    }

    @Override
    public StreamObserver<DataEnvelope> exchangeData(StreamObserver<TransferStatus> responseObserver) {
        return new StreamObserver<>() {
            private final Map<String, Long> processedBytesByStream = new HashMap<>();

            @Override
            public void onNext(DataEnvelope envelope) {
                String streamId = envelope.getStreamId().isBlank() ? "default" : envelope.getStreamId();
                long totalProcessed = processedBytesByStream.merge(streamId, (long) envelope.getPayload().size(), Long::sum);

                responseObserver.onNext(TransferStatus.newBuilder()
                        .setStreamId(streamId)
                        .setSequence(envelope.getSequence())
                        .setBytesProcessed(totalProcessed)
                        .setMessage(envelope.getEndOfStream() ? "stream complete" : "chunk received")
                        .setCompleted(envelope.getEndOfStream())
                        .build());
            }

            @Override
            public void onError(Throwable throwable) {
                LOGGER.log(Level.WARNING, "Bidirectional exchange terminated by client", throwable);
            }

            @Override
            public void onCompleted() {
                responseObserver.onCompleted();
            }
        };
    }

    private Path createStoragePath(String fileName) throws IOException {
        Files.createDirectories(storageDirectory);

        Path candidate = storageDirectory.resolve(fileName).normalize();
        if (candidate.startsWith(storageDirectory) && Files.notExists(candidate)) {
            return candidate;
        }

        Path uniquePath = storageDirectory.resolve(UUID.randomUUID() + "-" + fileName).normalize();
        if (!uniquePath.startsWith(storageDirectory)) {
            throw Status.INVALID_ARGUMENT
                    .withDescription("Resolved storage path is outside the upload directory")
                    .asRuntimeException();
        }

        return uniquePath;
    }

    private Path resolveDownloadPath(String fileName) {
        String safeFileName = sanitizeFileName(fileName);
        Path filePath = storageDirectory.resolve(safeFileName).normalize();

        if (!filePath.startsWith(storageDirectory)) {
            throw Status.INVALID_ARGUMENT
                    .withDescription("Requested file is outside the storage directory")
                    .asRuntimeException();
        }

        if (Files.notExists(filePath) || !Files.isRegularFile(filePath)) {
            throw Status.NOT_FOUND
                    .withDescription("Requested file does not exist")
                    .asRuntimeException();
        }

        return filePath;
    }

    private static String sanitizeFileName(String fileName) {
        if (fileName == null || fileName.isBlank()) {
            throw Status.INVALID_ARGUMENT.withDescription("File name must be provided").asRuntimeException();
        }

        Path normalized = Path.of(fileName).getFileName();
        if (normalized == null || normalized.toString().isBlank()) {
            throw Status.INVALID_ARGUMENT.withDescription("File name must be a valid path segment").asRuntimeException();
        }

        return normalized.toString();
    }

    private static MessageDigest newDigest() {
        try {
            return MessageDigest.getInstance("SHA-256");
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 digest is unavailable", e);
        }
    }

    private static String sha256(Path filePath) throws IOException {
        MessageDigest digest = newDigest();
        byte[] buffer = new byte[DEFAULT_CHUNK_SIZE];

        try (BufferedInputStream inputStream = new BufferedInputStream(Files.newInputStream(filePath, StandardOpenOption.READ))) {
            int bytesRead;
            while ((bytesRead = inputStream.read(buffer)) != -1) {
                digest.update(buffer, 0, bytesRead);
            }
        }

        return HexFormat.of().formatHex(digest.digest());
    }
}