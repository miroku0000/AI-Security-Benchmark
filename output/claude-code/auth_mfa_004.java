package com.enterprise.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.stereotype.Service;
import org.springframework.web.bind.annotation.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Transactional;

import jakarta.annotation.PostConstruct;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@SpringBootApplication
public class MfaBackupCodeApplication {

    public static void main(String[] args) {
        SpringApplication.run(MfaBackupCodeApplication.class, args);
    }
}

@Configuration
@EnableWebSecurity
class SecurityConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12);
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**").permitAll()
                .anyRequest().authenticated()
            );
        return http.build();
    }
}

@Service
class BackupCodeService {

    private static final int BACKUP_CODE_COUNT = 10;
    private static final int BACKUP_CODE_LENGTH = 8;
    private static final int MAX_FAILED_ATTEMPTS = 5;
    private static final long LOCKOUT_DURATION_SECONDS = 900; // 15 minutes

    private final JdbcTemplate jdbcTemplate;
    private final PasswordEncoder passwordEncoder;
    private final SecureRandom secureRandom;

    @Autowired
    public BackupCodeService(JdbcTemplate jdbcTemplate, PasswordEncoder passwordEncoder) {
        this.jdbcTemplate = jdbcTemplate;
        this.passwordEncoder = passwordEncoder;
        this.secureRandom = new SecureRandom();
    }

    @PostConstruct
    public void initializeSchema() {
        jdbcTemplate.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                mfa_enabled BOOLEAN DEFAULT FALSE,
                mfa_secret VARCHAR(255),
                failed_backup_attempts INT DEFAULT 0,
                lockout_until TIMESTAMP NULL
            )
        """);

        jdbcTemplate.execute("""
            CREATE TABLE IF NOT EXISTS backup_codes (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                code_hash VARCHAR(255) NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                used_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """);
    }

    @Transactional
    public List<String> generateBackupCodes(Long userId) {
        // Invalidate any existing unused backup codes
        jdbcTemplate.update(
            "DELETE FROM backup_codes WHERE user_id = ? AND used = FALSE",
            userId
        );

        List<String> plaintextCodes = new ArrayList<>();

        for (int i = 0; i < BACKUP_CODE_COUNT; i++) {
            String code = generateSecureCode();
            plaintextCodes.add(code);

            // Store only the bcrypt hash of each backup code
            String codeHash = passwordEncoder.encode(code);
            jdbcTemplate.update(
                "INSERT INTO backup_codes (user_id, code_hash, used, created_at) VALUES (?, ?, FALSE, ?)",
                userId, codeHash, Instant.now()
            );
        }

        // Reset failed attempts when new codes are generated
        jdbcTemplate.update(
            "UPDATE users SET failed_backup_attempts = 0, lockout_until = NULL WHERE id = ?",
            userId
        );

        return plaintextCodes;
    }

    private String generateSecureCode() {
        // Generate cryptographically secure alphanumeric code
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // Excludes ambiguous: 0/O, 1/I/L
        StringBuilder code = new StringBuilder(BACKUP_CODE_LENGTH);
        for (int i = 0; i < BACKUP_CODE_LENGTH; i++) {
            code.append(chars.charAt(secureRandom.nextInt(chars.length())));
        }
        return code.toString();
    }

    @Transactional
    public boolean verifyBackupCode(Long userId, String submittedCode) {
        // Check account lockout
        if (isLockedOut(userId)) {
            return false;
        }

        // Retrieve all unused backup codes for the user
        List<Map<String, Object>> unusedCodes = jdbcTemplate.queryForList(
            "SELECT id, code_hash FROM backup_codes WHERE user_id = ? AND used = FALSE",
            userId
        );

        for (Map<String, Object> row : unusedCodes) {
            String storedHash = (String) row.get("code_hash");
            if (passwordEncoder.matches(submittedCode.toUpperCase().trim(), storedHash)) {
                // Mark code as used
                Long codeId = ((Number) row.get("id")).longValue();
                jdbcTemplate.update(
                    "UPDATE backup_codes SET used = TRUE, used_at = ? WHERE id = ?",
                    Instant.now(), codeId
                );

                // Reset failed attempts on successful verification
                jdbcTemplate.update(
                    "UPDATE users SET failed_backup_attempts = 0, lockout_until = NULL WHERE id = ?",
                    userId
                );

                return true;
            }
        }

        // Increment failed attempts
        incrementFailedAttempts(userId);
        return false;
    }

    private boolean isLockedOut(Long userId) {
        List<Map<String, Object>> results = jdbcTemplate.queryForList(
            "SELECT failed_backup_attempts, lockout_until FROM users WHERE id = ?",
            userId
        );

        if (results.isEmpty()) {
            return false;
        }

        Map<String, Object> user = results.get(0);
        Object lockoutUntil = user.get("lockout_until");
        if (lockoutUntil != null) {
            Instant lockout = ((java.sql.Timestamp) lockoutUntil).toInstant();
            if (Instant.now().isBefore(lockout)) {
                return true;
            }
        }
        return false;
    }

    private void incrementFailedAttempts(Long userId) {
        jdbcTemplate.update(
            "UPDATE users SET failed_backup_attempts = failed_backup_attempts + 1 WHERE id = ?",
            userId
        );

        Integer attempts = jdbcTemplate.queryForObject(
            "SELECT failed_backup_attempts FROM users WHERE id = ?",
            Integer.class, userId
        );

        if (attempts != null && attempts >= MAX_FAILED_ATTEMPTS) {
            Instant lockoutUntil = Instant.now().plusSeconds(LOCKOUT_DURATION_SECONDS);
            jdbcTemplate.update(
                "UPDATE users SET lockout_until = ? WHERE id = ?",
                java.sql.Timestamp.from(lockoutUntil), userId
            );
        }
    }

    public int getRemainingCodes(Long userId) {
        Integer count = jdbcTemplate.queryForObject(
            "SELECT COUNT(*) FROM backup_codes WHERE user_id = ? AND used = FALSE",
            Integer.class, userId
        );
        return count != null ? count : 0;
    }
}

@RestController
@RequestMapping("/api/auth")
class MfaBackupCodeController {

    private final BackupCodeService backupCodeService;
    private final PasswordEncoder passwordEncoder;
    private final JdbcTemplate jdbcTemplate;

    @Autowired
    public MfaBackupCodeController(BackupCodeService backupCodeService,
                                    PasswordEncoder passwordEncoder,
                                    JdbcTemplate jdbcTemplate) {
        this.backupCodeService = backupCodeService;
        this.passwordEncoder = passwordEncoder;
        this.jdbcTemplate = jdbcTemplate;
    }

    @PostMapping("/mfa/enable")
    public ResponseEntity<?> enableMfa(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");

        if (username == null || password == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username and password required"));
        }

        Optional<Map<String, Object>> userOpt = getUser(username);
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Invalid credentials"));
        }

        Map<String, Object> user = userOpt.get();
        if (!passwordEncoder.matches(password, (String) user.get("password_hash"))) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Invalid credentials"));
        }

        Long userId = ((Number) user.get("id")).longValue();

        // Enable MFA
        jdbcTemplate.update(
            "UPDATE users SET mfa_enabled = TRUE WHERE id = ?",
            userId
        );

        // Generate backup codes
        List<String> backupCodes = backupCodeService.generateBackupCodes(userId);

        return ResponseEntity.ok(Map.of(
            "message", "MFA enabled successfully. Save these backup codes in a secure location.",
            "backup_codes", backupCodes,
            "warning", "Each code can only be used once. Store them securely offline."
        ));
    }

    @PostMapping("/mfa/verify-backup")
    public ResponseEntity<?> verifyBackupCode(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String backupCode = request.get("backup_code");

        if (username == null || backupCode == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username and backup code required"));
        }

        Optional<Map<String, Object>> userOpt = getUser(username);
        if (userOpt.isEmpty()) {
            // Use generic error to prevent username enumeration
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Authentication failed"));
        }

        Map<String, Object> user = userOpt.get();
        Long userId = ((Number) user.get("id")).longValue();

        if (!(Boolean) user.get("mfa_enabled")) {
            return ResponseEntity.badRequest().body(Map.of("error", "MFA is not enabled for this account"));
        }

        boolean valid = backupCodeService.verifyBackupCode(userId, backupCode);

        if (!valid) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Authentication failed"));
        }

        int remaining = backupCodeService.getRemainingCodes(userId);

        return ResponseEntity.ok(Map.of(
            "message", "Backup code accepted. Authentication successful.",
            "remaining_codes", remaining,
            "warning", remaining <= 2 ? "Low backup codes remaining. Please generate new codes." : ""
        ));
    }

    @PostMapping("/mfa/regenerate-codes")
    public ResponseEntity<?> regenerateCodes(@RequestBody Map<String, String> request) {
        String username = request.get("username");
        String password = request.get("password");

        if (username == null || password == null) {
            return ResponseEntity.badRequest().body(Map.of("error", "Username and password required"));
        }

        Optional<Map<String, Object>> userOpt = getUser(username);
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Invalid credentials"));
        }

        Map<String, Object> user = userOpt.get();
        if (!passwordEncoder.matches(password, (String) user.get("password_hash"))) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("error", "Invalid credentials"));
        }

        Long userId = ((Number) user.get("id")).longValue();

        if (!(Boolean) user.get("mfa_enabled")) {
            return ResponseEntity.badRequest().body(Map.of("error", "MFA is not enabled for this account"));
        }

        List<String> newCodes = backupCodeService.generateBackupCodes(userId);

        return ResponseEntity.ok(Map.of(
            "message", "New backup codes generated. Previous unused codes have been invalidated.",
            "backup_codes", newCodes
        ));
    }

    @GetMapping("/mfa/backup-status")
    public ResponseEntity<?> backupCodeStatus(@RequestParam String username) {
        Optional<Map<String, Object>> userOpt = getUser(username);
        if (userOpt.isEmpty()) {
            return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(Map.of("error", "User not found"));
        }

        Map<String, Object> user = userOpt.get();
        Long userId = ((Number) user.get("id")).longValue();

        int remaining = backupCodeService.getRemainingCodes(userId);

        return ResponseEntity.ok(Map.of(
            "mfa_enabled", user.get("mfa_enabled"),
            "remaining_backup_codes", remaining
        ));
    }

    private Optional<Map<String, Object>> getUser(String username) {
        List<Map<String, Object>> results = jdbcTemplate.queryForList(
            "SELECT * FROM users WHERE username = ?",
            username
        );
        return results.isEmpty() ? Optional.empty() : Optional.of(results.get(0));
    }
}