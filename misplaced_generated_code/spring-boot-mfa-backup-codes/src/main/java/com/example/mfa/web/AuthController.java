package com.example.mfa.web;

import com.example.mfa.service.AuthService;
import com.example.mfa.web.dto.LoginRequest;
import com.example.mfa.web.dto.MfaVerifyRequest;
import com.example.mfa.web.dto.RegisterRequest;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

  private final AuthService authService;

  public AuthController(AuthService authService) {
    this.authService = authService;
  }

  @PostMapping("/register")
  public ResponseEntity<Void> register(@Valid @RequestBody RegisterRequest req) {
    authService.register(req.getUsername(), req.getPassword());
    return ResponseEntity.ok().build();
  }

  @PostMapping("/login")
  public ResponseEntity<Map<String, Object>> login(@Valid @RequestBody LoginRequest req) {
    AuthService.LoginResult r = authService.login(req.getUsername(), req.getPassword());
    if (r.mfaRequired()) {
      return ResponseEntity.ok(
          Map.of("mfaRequired", true, "mfaToken", r.mfaToken()));
    }
    return ResponseEntity.ok(Map.of("accessToken", r.accessToken()));
  }

  @PostMapping("/mfa/verify")
  public ResponseEntity<Map<String, String>> verifyMfa(
      @RequestHeader(HttpHeaders.AUTHORIZATION) String authorization,
      @RequestBody(required = false) MfaVerifyRequest body) {
    if (authorization == null || !authorization.startsWith("Bearer ")) {
      return ResponseEntity.badRequest().build();
    }
    String mfaToken = authorization.substring(7);
    Integer totp = body != null ? body.getTotpCode() : null;
    String backup = body != null ? body.getBackupCode() : null;
    String access = authService.completeMfa(mfaToken, totp, backup);
    return ResponseEntity.ok(Map.of("accessToken", access));
  }
}
