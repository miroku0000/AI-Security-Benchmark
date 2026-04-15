package com.dataproc.grpc;

import com.dataproc.grpc.v1.DataTransferServiceGrpc;
import com.dataproc.grpc.v1.StreamEnvelope;
import com.dataproc.grpc.v1.StreamReply;
import com.dataproc.grpc.v1.UploadAck;
import com.dataproc.grpc.v1.UploadChunk;
import com.google.protobuf.ByteString;
import io.grpc.ManagedChannel;
import io.grpc.netty.shaded.io.grpc.netty.NettyChannelBuilder;
import io.grpc.stub.StreamObserver;

import java.nio.charset.StandardCharsets;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public final class DataTransferClientMain {

    private static final String HOST = System.getProperty("grpc.host", "localhost");
    private static final int PORT = Integer.parseInt(System.getProperty("grpc.port", "50051"));
    private static final int MAX_MESSAGE = Integer.parseInt(System.getProperty("grpc.maxMessageBytes", String.valueOf(Integer.MAX_VALUE)));
    private static final int MAX_METADATA = Integer.parseInt(System.getProperty("grpc.maxMetadataBytes", String.valueOf(16 * 1024 * 1024)));

    public static void main(String[] args) throws Exception {
        ManagedChannel channel = NettyChannelBuilder.forAddress(HOST, PORT)
                .usePlaintext()
                .maxInboundMessageSize(MAX_MESSAGE)
                .maxInboundMetadataSize(MAX_METADATA)
                .build();
        try {
            DataTransferServiceGrpc.DataTransferServiceStub stub = DataTransferServiceGrpc.newStub(channel);
            demoUpload(stub);
            demoBidi(stub);
        } finally {
            channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
        }
    }

    private static void demoUpload(DataTransferServiceGrpc.DataTransferServiceStub stub) throws Exception {
        CountDownLatch done = new CountDownLatch(1);
        StreamObserver<UploadAck> resp = new StreamObserver<>() {
            @Override
            public void onNext(UploadAck value) {
                System.out.println("upload ack bytes=" + value.getBytesReceived() + " resource=" + value.getResourceId());
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
        StreamObserver<UploadChunk> req = stub.uploadFile(resp);
        String sid = "demo-session";
        req.onNext(UploadChunk.newBuilder()
                .setSessionId(sid)
                .putMetadata("filename", "hello.bin")
                .setPayload(ByteString.copyFrom("hello-grpc-stream".getBytes(StandardCharsets.UTF_8)))
                .setOffset(0)
                .setLast(true)
                .build());
        req.onCompleted();
        done.await(30, TimeUnit.SECONDS);
    }

    private static void demoBidi(DataTransferServiceGrpc.DataTransferServiceStub stub) throws Exception {
        CountDownLatch done = new CountDownLatch(1);
        StreamObserver<StreamReply> resp = new StreamObserver<>() {
            @Override
            public void onNext(StreamReply value) {
                System.out.println("bidi reply corr=" + value.getCorrelationId() + " bytes=" + value.getPayload().size());
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
        StreamObserver<StreamEnvelope> req = stub.bidirectionalTransfer(resp);
        req.onNext(StreamEnvelope.newBuilder()
                .setCorrelationId("c1")
                .setPayload(ByteString.copyFromUtf8("ping"))
                .putHeaders("x-trace", "1")
                .setEndOfMessage(true)
                .build());
        req.onCompleted();
        done.await(30, TimeUnit.SECONDS);
    }
}
