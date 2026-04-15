package com.example.mfa.service;

import com.example.mfa.config.MfaProperties;
import com.example.mfa.model.BackupCode;
import com.example.mfa.model.User;
import com.example.mfa.repo.BackupCodeRepository;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BackupCodeService {

  private static final String ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";

  private final BackupCodeRepository backupCodeRepository;
  private final PasswordEncoder passwordEncoder;
  private final MfaProperties mfaProperties;
  private final SecureRandom secureRandom = new SecureRandom();

  public BackupCodeService(
      BackupCodeRepository backupCodeRepository,
      PasswordEncoder passwordEncoder,
      MfaProperties mfaProperties) {
    this.backupCodeRepository = backupCodeRepository;
    this.passwordEncoder = passwordEncoder;
    this.mfaProperties = mfaProperties;
  }

  @Transactional
  public List<String> replaceAndPersistCodes(User user) {
    backupCodeRepository.deleteByUser(user);
    backupCodeRepository.flush();
    int count = mfaProperties.getCount();
    int length = mfaProperties.getLength();
    List<String> plain = new ArrayList<>(count);
    List<BackupCode> rows = new ArrayList<>(count);
    for (int i = 0; i < count; i++) {
      String code = generatePlainCode(length);
      plain.add(formatDisplay(code));
      BackupCode bc = new BackupCode();
      bc.setUser(user);
      bc.setCodeHash(passwordEncoder.encode(normalize(code)));
      bc.setUsed(false);
      rows.add(bc);
    }
    backupCodeRepository.saveAll(rows);
    return plain;
  }

  private String generatePlainCode(int length) {
    StringBuilder sb = new StringBuilder(length);
    for (int i = 0; i < length; i++) {
      sb.append(ALPHABET.charAt(secureRandom.nextInt(ALPHABET.length())));
    }
    return sb.toString();
  }

  private String formatDisplay(String raw) {
    if (raw.length() <= 5) {
      return raw;
    }
    StringBuilder sb = new StringBuilder();
    for (int i = 0; i < raw.length(); i++) {
      if (i > 0 && i % 5 == 0) {
        sb.append('-');
      }
      sb.append(raw.charAt(i));
    }
    return sb.toString();
  }

  public static String normalize(String input) {
    if (input == null) {
      return "";
    }
    return input.replace("-", "").replace(" ", "").toUpperCase();
  }

  @Transactional
  public boolean verifyAndConsume(User user, String plainInput) {
    String norm = normalize(plainInput);
    if (norm.isEmpty()) {
      return false;
    }
    List<BackupCode> candidates = backupCodeRepository.findByUserAndUsedFalse(user);
    for (BackupCode bc : candidates) {
      if (passwordEncoder.matches(norm, bc.getCodeHash())) {
        bc.setUsed(true);
        bc.setUsedAt(Instant.now());
        backupCodeRepository.save(bc);
        return true;
      }
    }
    return false;
  }
}
