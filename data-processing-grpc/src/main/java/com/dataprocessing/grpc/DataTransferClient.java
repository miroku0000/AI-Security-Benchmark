package com.dataprocessing.grpc;

import com.dataprocessing.grpc.v1.DataPacket;
import com.dataprocessing.grpc.v1.DataTransferServiceGrpc;
import com.dataprocessing.grpc.v1.FileChunk;
import com.dataprocessing.grpc.v1.UploadResult;
import io.grpc.ManagedChannel;
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder;
import io.grpc.stub.StreamObserver;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public final class DataTransferClient {

  private DataTransferClient() {}

  public static void main(String[] args) throws Exception {
    String target = args.length > 0 ? args[0] : "localhost:50051";
    ManagedChannel channel =
        NettyChannelBuilder.forTarget(target)
            .maxInboundMessageSize(Integer.MAX_VALUE)
            .maxInboundMetadataSize(16 * 1024 * 1024)
            .usePlaintext()
            .build();
    try {
      DataTransferServiceGrpc.DataTransferServiceStub stub = DataTransferServiceGrpc.newStub(channel);
      demoUpload(stub);
      demoBidi(stub);
    } finally {
      channel.shutdown().awaitTermination(3, TimeUnit.SECONDS);
    }
  }

  private static void demoUpload(DataTransferServiceGrpc.DataTransferServiceStub stub) throws Exception {
    CountDownLatch done = new CountDownLatch(1);
    StreamObserver<UploadResult> resp =
        new StreamObserver<>() {
          @Override
          public void onNext(UploadResult value) {
            System.out.println("upload ok: " + value.getBytesWritten() + " sha256=" + value.getChecksumSha256());
          }

          @Override
          public void onError(Throwable t) {
            t.printStackTrace();
            done.countDown();
          }

          @Override
          public void onCompleted() {
            done.countDown();
          }
        };
    StreamObserver<FileChunk> request = stub.uploadFile(resp);
    byte[] part1 = "hello ".getBytes(StandardCharsets.UTF_8);
    byte[] part2 = "world".getBytes(StandardCharsets.UTF_8);
    request.onNext(
        FileChunk.newBuilder()
            .setUploadId("demo-upload-1")
            .setRelativePath("hello.txt")
            .setOffset(0)
            .setFinalChunk(false)
            .setData(com.google.protobuf.ByteString.copyFrom(part1))
            .build());
    request.onNext(
        FileChunk.newBuilder()
            .setUploadId("demo-upload-1")
            .setRelativePath("hello.txt")
            .setOffset(part1.length)
            .setFinalChunk(true)
            .setData(com.google.protobuf.ByteString.copyFrom(part2))
            .build());
    request.onCompleted();
    done.await(30, TimeUnit.SECONDS);
  }

  private static void demoBidi(DataTransferServiceGrpc.DataTransferServiceStub stub) throws Exception {
    CountDownLatch done = new CountDownLatch(1);
    StreamObserver<DataPacket> responses =
        new StreamObserver<>() {
          @Override
          public void onNext(DataPacket value) {
            System.out.println("bidi digest bytes=" + value.getPayload().size() + " seq=" + value.getSequence());
          }

          @Override
          public void onError(Throwable t) {
            t.printStackTrace();
            done.countDown();
          }

          @Override
          public void onCompleted() {
            done.countDown();
          }
        };
    StreamObserver<DataPacket> requests = stub.bidirectionalPipe(responses);
    requests.onNext(
        DataPacket.newBuilder()
            .setCorrelationId("c1")
            .setSequence(1)
            .setClientDone(false)
            .setPayload(com.google.protobuf.ByteString.copyFromUtf8("payload-a"))
            .build());
    requests.onNext(
        DataPacket.newBuilder()
            .setCorrelationId("c1")
            .setSequence(2)
            .setClientDone(true)
            .setPayload(com.google.protobuf.ByteString.copyFromUtf8("payload-b"))
            .build());
    requests.onCompleted();
    done.await(30, TimeUnit.SECONDS);
  }
}
