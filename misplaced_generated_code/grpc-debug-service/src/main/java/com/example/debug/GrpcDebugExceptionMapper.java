package com.example.debug;

import com.google.protobuf.Any;
import com.google.rpc.DebugInfo;
import com.google.rpc.ErrorInfo;
import com.google.rpc.Status;
import io.grpc.StatusRuntimeException;
import io.grpc.protobuf.StatusProto;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.sql.SQLException;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

public final class GrpcDebugExceptionMapper {

  private GrpcDebugExceptionMapper() {}

  public static StatusRuntimeException toStatusRuntimeException(
      Throwable throwable, InternalServiceState internalState) {
    String fullMessage = buildFullMessage(throwable);
    String stackTrace = stackTraceToString(throwable);

    DebugInfo debugInfo =
        DebugInfo.newBuilder()
            .setDetail(fullMessage)
            .addAllStackEntries(Arrays.asList(stackTrace.split("\n")))
            .build();

    Map<String, String> meta = new LinkedHashMap<>();
    meta.putAll(internalState.snapshot());
    meta.put("exception_class", throwable.getClass().getName());
    if (throwable.getCause() != null) {
      meta.put("cause_class", throwable.getCause().getClass().getName());
      meta.put("cause_message", String.valueOf(throwable.getCause().getMessage()));
    }
    appendSqlMetadata(throwable, meta);

    ErrorInfo.Builder errorInfoBuilder =
        ErrorInfo.newBuilder().setReason("INTERNAL_DEBUG").setDomain("debug.example.com");
    for (Map.Entry<String, String> e : meta.entrySet()) {
      errorInfoBuilder.putMetadata(e.getKey(), e.getValue());
    }

    Status rpcStatus =
        Status.newBuilder()
            .setCode(com.google.rpc.Code.INTERNAL.getNumber())
            .setMessage(fullMessage)
            .addDetails(Any.pack(debugInfo))
            .addDetails(Any.pack(errorInfoBuilder.build()))
            .build();

    StatusRuntimeException base = StatusProto.toStatusRuntimeException(rpcStatus);
    return new StatusRuntimeException(base.getStatus(), base.getTrailers(), throwable);
  }

  private static void appendSqlMetadata(Throwable throwable, Map<String, String> meta) {
    Throwable t = throwable;
    while (t != null) {
      if (t instanceof SQLException sqlEx) {
        meta.put("sql_state", sqlEx.getSQLState() != null ? sqlEx.getSQLState() : "");
        meta.put("sql_error_code", Integer.toString(sqlEx.getErrorCode()));
        meta.put("sql_message", sqlEx.getMessage() != null ? sqlEx.getMessage() : "");
        SQLException next = sqlEx.getNextException();
        if (next != null) {
          meta.put("sql_next_message", next.getMessage() != null ? next.getMessage() : "");
          meta.put("sql_next_state", next.getSQLState() != null ? next.getSQLState() : "");
        }
      }
      t = t.getCause();
    }
  }

  private static String buildFullMessage(Throwable throwable) {
    StringBuilder sb = new StringBuilder();
    Throwable t = throwable;
    while (t != null) {
      if (sb.length() > 0) {
        sb.append(" | Caused by: ");
      }
      sb.append(t.getClass().getName()).append(": ").append(t.getMessage());
      t = t.getCause();
    }
    return sb.toString();
  }

  private static String stackTraceToString(Throwable throwable) {
    StringWriter sw = new StringWriter();
    PrintWriter pw = new PrintWriter(sw);
    throwable.printStackTrace(pw);
    pw.flush();
    return sw.toString();
  }
}
