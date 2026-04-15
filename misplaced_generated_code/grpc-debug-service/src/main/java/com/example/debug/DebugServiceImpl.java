package com.example.debug;

import com.example.debug.grpc.DebugServiceGrpc;
import com.example.debug.grpc.PingRequest;
import com.example.debug.grpc.PingResponse;
import com.example.debug.grpc.SimulateDbFailureRequest;
import com.example.debug.grpc.SimulateDbFailureResponse;
import io.grpc.stub.StreamObserver;
import java.sql.SQLException;

public class DebugServiceImpl extends DebugServiceGrpc.DebugServiceImplBase {

  private final InternalServiceState state;

  public DebugServiceImpl(InternalServiceState state) {
    this.state = state;
  }

  @Override
  public void ping(PingRequest request, StreamObserver<PingResponse> responseObserver) {
    try {
      state.recordRequest("ping", request.getClientId());
      if ("fail".equalsIgnoreCase(request.getClientId())) {
        throw new IllegalArgumentException("forced failure for client_id=fail");
      }
      responseObserver.onNext(
          PingResponse.newBuilder().setMessage("ok: " + request.getClientId()).build());
      responseObserver.onCompleted();
    } catch (Throwable t) {
      responseObserver.onError(GrpcDebugExceptionMapper.toStatusRuntimeException(t, state));
    }
  }

  @Override
  public void simulateDbFailure(
      SimulateDbFailureRequest request, StreamObserver<SimulateDbFailureResponse> responseObserver) {
    try {
      state.recordRequest("simulateDbFailure", request.getScenario());
      FakeDatabase.runQuery(request.getScenario());
      responseObserver.onNext(SimulateDbFailureResponse.newBuilder().setResult("unexpected").build());
      responseObserver.onCompleted();
    } catch (SQLException ex) {
      responseObserver.onError(GrpcDebugExceptionMapper.toStatusRuntimeException(ex, state));
    } catch (Throwable t) {
      responseObserver.onError(GrpcDebugExceptionMapper.toStatusRuntimeException(t, state));
    }
  }
}
