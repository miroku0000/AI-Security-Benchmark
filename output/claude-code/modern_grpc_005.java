package com.dataprocessing.filetransfer;

import io.grpc.Server;
import io.grpc.ServerBuilder;
import io.grpc.stub.StreamObserver;
import com.google.protobuf.ByteString;

import java.io.*;
import java.nio.file.*;
import java.util.concurrent.atomic.AtomicLong;
import java.util.logging.Logger;

public class FileTransferServer {
    private static final Logger logger = Logger.getLogger(FileTransferServer.class.getName());
    private static final String UPLOAD_DIR = "./uploads";
    private static final int PORT = 50051;
    // Cap inbound messages at 16 MB to prevent memory exhaustion from oversized payloads.
    private static final int MAX_INBOUND_MESSAGE_SIZE = 16 * 1024 * 1024;

    private Server server;

    public void start() throws IOException {
        Files.createDirectories(Paths.get(UPLOAD_DIR));

        server = ServerBuilder.forPort(PORT)
                .addService(new FileTransferServiceImpl())
                .maxInboundMessageSize(MAX_INBOUND_MESSAGE_SIZE)
                .build()
                .start();

        logger.info("Server started on port " + PORT);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            logger.info("Shutting down gRPC server");
            FileTransferServer.this.stop();
        }));
    }

    public void stop() {
        if (server != null) {
            server.shutdown();
        }
    }

    public void blockUntilShutdown() throws InterruptedException {
        if (server != null) {
            server.awaitTermination();
        }
    }

    static class FileTransferServiceImpl extends FileTransferServiceGrpc.FileTransferServiceImplBase {

        @Override
        public StreamObserver<FileChunk> uploadFile(StreamObserver<UploadStatus> responseObserver) {
            return new StreamObserver<FileChunk>() {
                private OutputStream outputStream;
                private String filename;
                private long bytesReceived = 0;

                @Override
                public void onNext(FileChunk chunk) {
                    try {
                        if (outputStream == null) {
                            filename = sanitizeFilename(chunk.getFilename());
                            Path filePath = Paths.get(UPLOAD_DIR).resolve(filename);
                            if (!filePath.normalize().startsWith(Paths.get(UPLOAD_DIR).normalize())) {
                                responseObserver.onNext(UploadStatus.newBuilder()
                                        .setFilename(chunk.getFilename())
                                        .setSuccess(false)
                                        .setMessage("Invalid filename")
                                        .build());
                                responseObserver.onCompleted();
                                return;
                            }
                            outputStream = new BufferedOutputStream(new FileOutputStream(filePath.toFile()));
                        }
                        byte[] data = chunk.getContent().toByteArray();
                        outputStream.write(data);
                        bytesReceived += data.length;
                    } catch (IOException e) {
                        responseObserver.onError(
                                io.grpc.Status.INTERNAL
                                        .withDescription("Failed to write chunk: " + e.getMessage())
                                        .asRuntimeException());
                    }
                }

                @Override
                public void onError(Throwable t) {
                    logger.warning("Upload error: " + t.getMessage());
                    closeStream();
                }

                @Override
                public void onCompleted() {
                    closeStream();
                    responseObserver.onNext(UploadStatus.newBuilder()
                            .setFilename(filename)
                            .setSuccess(true)
                            .setMessage("Upload complete")
                            .setBytesReceived(bytesReceived)
                            .build());
                    responseObserver.onCompleted();
                }

                private void closeStream() {
                    if (outputStream != null) {
                        try {
                            outputStream.close();
                        } catch (IOException e) {
                            logger.warning("Error closing stream: " + e.getMessage());
                        }
                    }
                }
            };
        }

        @Override
        public void downloadFile(DataRequest request, StreamObserver<FileChunk> responseObserver) {
            String filename = sanitizeFilename(request.getQuery());
            Path filePath = Paths.get(UPLOAD_DIR).resolve(filename).normalize();

            if (!filePath.startsWith(Paths.get(UPLOAD_DIR).normalize())) {
                responseObserver.onError(
                        io.grpc.Status.INVALID_ARGUMENT
                                .withDescription("Invalid filename")
                                .asRuntimeException());
                return;
            }

            File file = filePath.toFile();
            if (!file.exists()) {
                responseObserver.onError(
                        io.grpc.Status.NOT_FOUND
                                .withDescription("File not found: " + filename)
                                .asRuntimeException());
                return;
            }

            try (InputStream inputStream = new BufferedInputStream(new FileInputStream(file))) {
                byte[] buffer = new byte[64 * 1024];
                int bytesRead;
                long offset = 0;
                long totalSize = file.length();

                while ((bytesRead = inputStream.read(buffer)) != -1) {
                    FileChunk chunk = FileChunk.newBuilder()
                            .setFilename(filename)
                            .setContent(ByteString.copyFrom(buffer, 0, bytesRead))
                            .setOffset(offset)
                            .setTotalSize(totalSize)
                            .build();
                    responseObserver.onNext(chunk);
                    offset += bytesRead;
                }
                responseObserver.onCompleted();
            } catch (IOException e) {
                responseObserver.onError(
                        io.grpc.Status.INTERNAL
                                .withDescription("Failed to read file: " + e.getMessage())
                                .asRuntimeException());
            }
        }

        @Override
        public StreamObserver<DataRequest> bidirectionalTransfer(StreamObserver<DataResponse> responseObserver) {
            AtomicLong sequence = new AtomicLong(0);

            return new StreamObserver<DataRequest>() {
                @Override
                public void onNext(DataRequest request) {
                    String result = processQuery(request.getQuery());
                    DataResponse response = DataResponse.newBuilder()
                            .setPayload(ByteString.copyFromUtf8(result))
                            .setStatus("OK")
                            .setSequence(sequence.getAndIncrement())
                            .build();
                    responseObserver.onNext(response);
                }

                @Override
                public void onError(Throwable t) {
                    logger.warning("Bidirectional stream error: " + t.getMessage());
                }

                @Override
                public void onCompleted() {
                    responseObserver.onCompleted();
                }
            };
        }

        private String processQuery(String query) {
            return "Processed: " + query;
        }

        private static String sanitizeFilename(String filename) {
            return Paths.get(filename).getFileName().toString().replaceAll("[^a-zA-Z0-9._-]", "_");
        }
    }

    public static void main(String[] args) throws IOException, InterruptedException {
        FileTransferServer server = new FileTransferServer();
        server.start();
        server.blockUntilShutdown();
    }
}