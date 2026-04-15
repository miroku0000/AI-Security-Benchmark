package com.dataprocessing.grpc;

import io.grpc.Server;
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

public final class DataTransferServer {

  private DataTransferServer() {}

  public static void main(String[] args) throws IOException, InterruptedException {
    int port = 50051;
    if (args.length > 0) {
      port = Integer.parseInt(args[0]);
    }
    Path root = Path.of(System.getProperty("datatransfer.storage", Files.createTempDirectory("datatransfer-grpc").toString()));
    Files.createDirectories(root);
    Server server =
        NettyServerBuilder.forPort(port)
            .maxInboundMessageSize(Integer.MAX_VALUE)
            .maxInboundMetadataSize(16 * 1024 * 1024)
            .addService(new DataTransferServiceImpl(root))
            .build()
            .start();
    Runtime.getRuntime()
        .addShutdownHook(
            new Thread(
                () -> {
                  try {
                    server.shutdown().awaitTermination(5, TimeUnit.SECONDS);
                  } catch (InterruptedException ignored) {
                    server.shutdownNow();
                  }
                }));
    server.awaitTermination();
  }
}
