package com.example.debug;

import com.example.debug.grpc.DebugServiceGrpc;
import com.example.debug.grpc.SimulateDbFailureRequest;
import io.grpc.ManagedChannel;
import io.grpc.StatusRuntimeException;
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder;
import io.grpc.protobuf.StatusProto;

public final class DebugGrpcClient {

  private DebugGrpcClient() {}

  public static void main(String[] args) {
    String target = args.length > 0 ? args[0] : "localhost:50051";
    ManagedChannel channel = NettyChannelBuilder.forTarget(target).usePlaintext().build();
    try {
      DebugServiceGrpc.DebugServiceBlockingStub stub =
          DebugServiceGrpc.newBlockingStub(channel);
      try {
        stub.simulateDbFailure(
            SimulateDbFailureRequest.newBuilder().setScenario("").build());
      } catch (StatusRuntimeException ex) {
        System.out.println(ex.getStatus());
        System.out.println(ex.getMessage());
        com.google.rpc.Status status = StatusProto.fromThrowable(ex);
        if (status != null) {
          System.out.println("google.rpc.Status: " + status);
        }
      }
    } finally {
      channel.shutdown();
    }
  }
}
