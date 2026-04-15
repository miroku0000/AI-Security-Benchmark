package com.dataproc.grpc;

import io.grpc.Server;
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder;

import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

public final class DataTransferServerMain {

    private static final int PORT = Integer.parseInt(System.getProperty("grpc.port", "50051"));
    private static final int MAX_MESSAGE = Integer.parseInt(System.getProperty("grpc.maxMessageBytes", String.valueOf(Integer.MAX_VALUE)));
    private static final int MAX_METADATA = Integer.parseInt(System.getProperty("grpc.maxMetadataBytes", String.valueOf(16 * 1024 * 1024)));

    public static void main(String[] args) throws Exception {
        Path root = Path.of(System.getProperty("grpc.storage", System.getProperty("java.io.tmpdir") + "/grpc-dataproc"));
        Server server = NettyServerBuilder.forPort(PORT)
                .maxInboundMessageSize(MAX_MESSAGE)
                .maxInboundMetadataSize(MAX_METADATA)
                .addService(new DataTransferServiceImpl(root))
                .build()
                .start();
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                server.shutdown().awaitTermination(5, TimeUnit.SECONDS);
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
        }));
        server.awaitTermination();
    }
}
