package com.example.mfa.web;

import com.example.mfa.security.UserPrincipal;
import com.example.mfa.service.AuthService;
import com.example.mfa.web.dto.ActivateMfaRequest;
import jakarta.validation.Valid;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/mfa")
public class MfaController {

  private final AuthService authService;

  public MfaController(AuthService authService) {
    this.authService = authService;
  }

  @PostMapping("/setup")
  public ResponseEntity<Map<String, Object>> setup(@AuthenticationPrincipal UserPrincipal principal) {
    AuthService.MfaSetupResult r = authService.startMfaSetup(principal.getUsername());
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("base32Secret", r.base32Secret());
    body.put("otpAuthUri", r.otpAuthUri());
    body.put("backupCodes", r.backupCodes());
    return ResponseEntity.ok(body);
  }

  @PostMapping("/activate")
  public ResponseEntity<Void> activate(
      @AuthenticationPrincipal UserPrincipal principal, @Valid @RequestBody ActivateMfaRequest req) {
    authService.activateMfa(principal.getUsername(), req.getTotpCode());
    return ResponseEntity.ok().build();
  }
}
