package com.example.debug;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

public final class InternalServiceState {

  private final AtomicLong requestCounter = new AtomicLong();
  private volatile String lastOperation = "none";
  private volatile String lastClientId = "";

  public void recordRequest(String operation, String clientId) {
    requestCounter.incrementAndGet();
    lastOperation = operation;
    lastClientId = clientId == null ? "" : clientId;
  }

  public Map<String, String> snapshot() {
    Map<String, String> m = new LinkedHashMap<>();
    m.put("request_count", Long.toString(requestCounter.get()));
    m.put("last_operation", lastOperation);
    m.put("last_client_id", lastClientId);
    m.put("thread", Thread.currentThread().getName());
    return Collections.unmodifiableMap(m);
  }
}