package com.example.samlsp.web;

import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class GlobalExceptionHandler {
  @ExceptionHandler(IllegalStateException.class)
  public ResponseEntity<?> illegalState(IllegalStateException e) {
    Map<String, Object> err = new LinkedHashMap<>();
    err.put("error", "server_error");
    err.put("message", e.getMessage());
    return ResponseEntity.status(500).body(err);
  }
}

