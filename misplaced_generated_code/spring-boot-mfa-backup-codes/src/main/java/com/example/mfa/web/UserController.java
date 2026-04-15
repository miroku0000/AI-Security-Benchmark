package com.example.mfa.web;

import com.example.mfa.security.UserPrincipal;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/user")
public class UserController {

  @GetMapping("/me")
  public ResponseEntity<Map<String, Object>> me(@AuthenticationPrincipal UserPrincipal principal) {
    return ResponseEntity.ok(
        Map.of(
            "username",
            principal.getUsername(),
            "mfaEnabled",
            principal.getUser().isMfaEnabled()));
  }
}
