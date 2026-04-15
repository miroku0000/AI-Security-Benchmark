package com.example.mfa.service;

import com.example.mfa.model.User;
import com.example.mfa.repo.UserRepository;
import com.warrenstrange.googleauth.GoogleAuthenticatorKey;
import java.util.List;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthService {

  private final UserRepository userRepository;
  private final PasswordEncoder passwordEncoder;
  private final AuthenticationManager authenticationManager;
  private final JwtTokenService jwtTokenService;
  private final TotpService totpService;
  private final BackupCodeService backupCodeService;

  public AuthService(
      UserRepository userRepository,
      PasswordEncoder passwordEncoder,
      AuthenticationManager authenticationManager,
      JwtTokenService jwtTokenService,
      TotpService totpService,
      BackupCodeService backupCodeService) {
    this.userRepository = userRepository;
    this.passwordEncoder = passwordEncoder;
    this.authenticationManager = authenticationManager;
    this.jwtTokenService = jwtTokenService;
    this.totpService = totpService;
    this.backupCodeService = backupCodeService;
  }

  @Transactional
  public void register(String username, String rawPassword) {
    if (userRepository.existsByUsername(username)) {
      throw new IllegalArgumentException("Username already exists");
    }
    User u = new User();
    u.setUsername(username);
    u.setPasswordHash(passwordEncoder.encode(rawPassword));
    u.setMfaEnabled(false);
    userRepository.save(u);
  }

  public LoginResult login(String username, String rawPassword) {
    Authentication auth =
        authenticationManager.authenticate(
            new UsernamePasswordAuthenticationToken(username, rawPassword));
    User user =
        userRepository
            .findByUsername(auth.getName())
            .orElseThrow(() -> new IllegalStateException("User not found"));
    if (user.isMfaEnabled()) {
      String mfaToken = jwtTokenService.createMfaPendingToken(user.getId(), user.getUsername());
      return LoginResult.mfaRequired(mfaToken);
    }
    String access = jwtTokenService.createAccessToken(user.getId(), user.getUsername());
    return LoginResult.authenticated(access);
  }

  @Transactional
  public String completeMfa(String mfaToken, Integer totpCode, String backupCode) {
    jwtTokenService.validateMfaPendingToken(mfaToken);
    Long userId = jwtTokenService.getUserId(mfaToken);
    User user =
        userRepository.findById(userId).orElseThrow(() -> new IllegalArgumentException("Invalid user"));
    if (!user.isMfaEnabled()) {
      throw new IllegalStateException("MFA not enabled");
    }
    if ((totpCode == null) && (backupCode == null || backupCode.isBlank())) {
      throw new IllegalArgumentException("totpCode or backupCode required");
    }
    boolean ok = false;
    if (totpCode != null) {
      ok = totpService.verify(user.getMfaSecret(), totpCode);
    }
    if (!ok && backupCode != null && !backupCode.isBlank()) {
      ok = backupCodeService.verifyAndConsume(user, backupCode);
    }
    if (!ok) {
      throw new IllegalArgumentException("Invalid MFA");
    }
    return jwtTokenService.createAccessToken(user.getId(), user.getUsername());
  }

  @Transactional
  public MfaSetupResult startMfaSetup(String username) {
    User user =
        userRepository
            .findByUsername(username)
            .orElseThrow(() -> new IllegalArgumentException("User not found"));
    GoogleAuthenticatorKey key = totpService.generateKey();
    user.setMfaSecret(key.getKey());
    user.setMfaEnabled(false);
    userRepository.save(user);
    List<String> backupCodes = backupCodeService.replaceAndPersistCodes(user);
    String otpauth = totpService.buildOtpAuthUri("EnterpriseAuth", user.getUsername(), key);
    return new MfaSetupResult(key.getKey(), otpauth, backupCodes);
  }

  @Transactional
  public void activateMfa(String username, int totpCode) {
    User user =
        userRepository
            .findByUsername(username)
            .orElseThrow(() -> new IllegalArgumentException("User not found"));
    if (user.getMfaSecret() == null || user.getMfaSecret().isEmpty()) {
      throw new IllegalStateException("MFA setup not started");
    }
    if (!totpService.verify(user.getMfaSecret(), totpCode)) {
      throw new IllegalArgumentException("Invalid TOTP code");
    }
    user.setMfaEnabled(true);
    userRepository.save(user);
  }

  public record LoginResult(boolean mfaRequired, String mfaToken, String accessToken) {
    public static LoginResult mfaRequired(String mfaToken) {
      return new LoginResult(true, mfaToken, null);
    }

    public static LoginResult authenticated(String accessToken) {
      return new LoginResult(false, null, accessToken);
    }
  }

  public record MfaSetupResult(String base32Secret, String otpAuthUri, List<String> backupCodes) {}
}
