package com.example.samlsp.web;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HelloController {
  @GetMapping("/hello")
  public Map<String, Object> hello() {
    return Map.of("ok", true);
  }
}

