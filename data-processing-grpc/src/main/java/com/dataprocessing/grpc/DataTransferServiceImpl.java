package com.dataprocessing.grpc;

import com.dataprocessing.grpc.v1.DataPacket;
import com.dataprocessing.grpc.v1.DataTransferServiceGrpc;
import com.dataprocessing.grpc.v1.FileChunk;
import com.dataprocessing.grpc.v1.FileRequest;
import com.dataprocessing.grpc.v1.UploadResult;
import io.grpc.Status;
import io.grpc.stub.StreamObserver;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.ByteBuffer;
import java.nio.channels.SeekableByteChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.DigestOutputStream;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;

public final class DataTransferServiceImpl extends DataTransferServiceGrpc.DataTransferServiceImplBase {

  private final Path storageRoot;
  private final Map<String, Path> resourceIndex = new ConcurrentHashMap<>();
  private static final int DOWNLOAD_CHUNK_BYTES = 256 * 1024;

  public DataTransferServiceImpl(Path storageRoot) {
    this.storageRoot = storageRoot;
  }

  @Override
  public StreamObserver<FileChunk> uploadFile(StreamObserver<UploadResult> responseObserver) {
    return new StreamObserver<>() {
      private Path target;
      private OutputStream out;
      private DigestOutputStream digestOut;
      private String uploadId;
      private long written;
      private boolean closed;

      @Override
      public void onNext(FileChunk chunk) {
        try {
          if (closed) {
            return;
          }
          if (uploadId == null) {
            uploadId = chunk.getUploadId().isEmpty() ? UUID.randomUUID().toString() : chunk.getUploadId();
            String safeName = sanitizePath(chunk.getRelativePath());
            Path dir = storageRoot.resolve(uploadId);
            Files.createDirectories(dir);
            target = dir.resolve(safeName.isEmpty() ? "payload.bin" : safeName);
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            out = Files.newOutputStream(target, StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING);
            digestOut = new DigestOutputStream(out, md);
          }
          if (!chunk.getUploadId().isEmpty() && !chunk.getUploadId().equals(uploadId)) {
            fail(Status.INVALID_ARGUMENT.withDescription("upload_id changed mid-stream"));
            return;
          }
          byte[] data = chunk.getData().toByteArray();
          if (data.length > 0) {
            digestOut.write(data);
            written += data.length;
          }
          if (chunk.getFinalChunk()) {
            finishOk();
          }
        } catch (IOException | NoSuchAlgorithmException e) {
          fail(Status.INTERNAL.withDescription(e.getMessage()).withCause(e));
        }
      }

      @Override
      public void onError(Throwable t) {
        cleanupQuietly();
      }

      @Override
      public void onCompleted() {
        try {
          if (closed) {
            return;
          }
          if (uploadId == null) {
            closed = true;
            responseObserver.onError(
                Status.INVALID_ARGUMENT.withDescription("upload stream contained no chunks").asRuntimeException());
            return;
          }
          finishOk();
        } catch (Exception e) {
          responseObserver.onError(Status.INTERNAL.withDescription(e.getMessage()).withCause(e).asRuntimeException());
        }
      }

      private void finishOk() throws IOException {
        if (closed) {
          return;
        }
        closed = true;
        String hex = "";
        if (digestOut != null) {
          digestOut.flush();
          hex = digestHex(digestOut.getMessageDigest().digest());
          digestOut.close();
        } else if (out != null) {
          out.close();
        }
        digestOut = null;
        out = null;
        resourceIndex.put(uploadId, target);
        UploadResult.Builder b =
            UploadResult.newBuilder()
                .setUploadId(uploadId)
                .setBytesWritten(written)
                .setStoredPath(target.toString())
                .setChecksumSha256(hex);
        responseObserver.onNext(b.build());
        responseObserver.onCompleted();
      }

      private static String digestHex(byte[] d) {
        StringBuilder sb = new StringBuilder(d.length * 2);
        for (byte x : d) {
          sb.append(String.format("%02x", x));
        }
        return sb.toString();
      }

      private void fail(Status status) {
        if (closed) {
          return;
        }
        closed = true;
        cleanupQuietly();
        responseObserver.onError(status.asRuntimeException());
      }

      private void cleanupQuietly() {
        try {
          if (digestOut != null) {
            digestOut.close();
          } else if (out != null) {
            out.close();
          }
        } catch (IOException ignored) {
        }
        digestOut = null;
        out = null;
      }
    };
  }

  @Override
  public void downloadFile(FileRequest request, StreamObserver<FileChunk> responseObserver) {
    try {
      Path path = resolveResource(request.getResourceId());
      if (path == null || !Files.isRegularFile(path)) {
        responseObserver.onError(Status.NOT_FOUND.asRuntimeException());
        return;
      }
      long size = Files.size(path);
      long offset = request.getOffset();
      if (offset < 0 || offset > size) {
        responseObserver.onError(Status.OUT_OF_RANGE.asRuntimeException());
        return;
      }
      long maxBytes = request.getMaxBytes() == 0 ? Long.MAX_VALUE : request.getMaxBytes();
      try (SeekableByteChannel ch = Files.newByteChannel(path, StandardOpenOption.READ)) {
        ch.position(offset);
        long sent = 0;
        ByteBuffer buf = ByteBuffer.allocate(DOWNLOAD_CHUNK_BYTES);
        while (sent < maxBytes) {
          int toRead = (int) Math.min(DOWNLOAD_CHUNK_BYTES, maxBytes - sent);
          buf.clear();
          buf.limit(toRead);
          int n = ch.read(buf);
          if (n <= 0) {
            break;
          }
          buf.flip();
          byte[] chunk = new byte[n];
          buf.get(chunk);
          long nextOffset = offset + sent;
          boolean last = n < toRead || nextOffset + n >= size || sent + n >= maxBytes;
          FileChunk.Builder fb =
              FileChunk.newBuilder()
                  .setUploadId(request.getResourceId())
                  .setRelativePath(path.getFileName().toString())
                  .setOffset(nextOffset)
                  .setFinalChunk(last)
                  .setData(com.google.protobuf.ByteString.copyFrom(chunk));
          fb.putAllHeaders(request.getHeadersMap());
          responseObserver.onNext(fb.build());
          sent += n;
          if (last) {
            break;
          }
        }
      }
      responseObserver.onCompleted();
    } catch (IOException e) {
      responseObserver.onError(Status.INTERNAL.withDescription(e.getMessage()).withCause(e).asRuntimeException());
    }
  }

  @Override
  public StreamObserver<DataPacket> bidirectionalPipe(StreamObserver<DataPacket> responseObserver) {
    return new StreamObserver<>() {
      private final AtomicBoolean responseDone = new AtomicBoolean();

      private void completeResponse() {
        if (responseDone.compareAndSet(false, true)) {
          responseObserver.onCompleted();
        }
      }

      @Override
      public void onNext(DataPacket packet) {
        try {
          MessageDigest md = MessageDigest.getInstance("SHA-256");
          byte[] body = packet.getPayload().toByteArray();
          md.update(body);
          byte[] digest = md.digest();
          DataPacket reply =
              DataPacket.newBuilder()
                  .setCorrelationId(packet.getCorrelationId())
                  .setSequence(packet.getSequence())
                  .setClientDone(packet.getClientDone())
                  .setPayload(com.google.protobuf.ByteString.copyFrom(digest))
                  .putAllAttributes(packet.getAttributesMap())
                  .putAttributes("bytes_received", Integer.toString(body.length))
                  .build();
          synchronized (responseObserver) {
            if (!responseDone.get()) {
              responseObserver.onNext(reply);
            }
          }
          if (packet.getClientDone()) {
            completeResponse();
          }
        } catch (NoSuchAlgorithmException e) {
          if (responseDone.compareAndSet(false, true)) {
            responseObserver.onError(Status.INTERNAL.withDescription(e.getMessage()).withCause(e).asRuntimeException());
          }
        }
      }

      @Override
      public void onError(Throwable t) {
        responseDone.set(true);
      }

      @Override
      public void onCompleted() {
        completeResponse();
      }
    };
  }

  private Path resolveResource(String resourceId) {
    if (resourceId == null || resourceId.isEmpty()) {
      return null;
    }
    Path indexed = resourceIndex.get(resourceId);
    if (indexed != null && Files.isRegularFile(indexed)) {
      return indexed;
    }
    Path p = storageRoot.resolve(resourceId);
    if (Files.isRegularFile(p)) {
      return p;
    }
    Path nested = storageRoot.resolve(resourceId).normalize();
    if (nested.startsWith(storageRoot) && Files.isRegularFile(nested)) {
      return nested;
    }
    return null;
  }

  private static String sanitizePath(String relative) {
    if (relative == null || relative.isEmpty()) {
      return "";
    }
    String n = relative.replace('\\', '/');
    int i = 0;
    while (i < n.length() && (n.charAt(i) == '/' || n.charAt(i) == '.')) {
      i++;
    }
    n = n.substring(i);
    if (n.contains("..")) {
      return "payload.bin";
    }
    int slash = n.lastIndexOf('/');
    return slash >= 0 ? n.substring(slash + 1) : n;
  }
}
