package com.example.debug;

import io.grpc.Server;
import io.grpc.netty.shaded.io.grpc.netty.NettyServerBuilder;
import java.io.IOException;
import java.util.concurrent.TimeUnit;

public final class DebugGrpcServer {

  private DebugGrpcServer() {}

  public static void main(String[] args) throws IOException, InterruptedException {
    int port = args.length > 0 ? Integer.parseInt(args[0]) : 50051;
    InternalServiceState state = new InternalServiceState();
    Server server =
        NettyServerBuilder.forPort(port)
            .addService(new DebugServiceImpl(state))
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
                    Thread.currentThread().interrupt();
                  }
                }));
    server.awaitTermination();
  }
}
