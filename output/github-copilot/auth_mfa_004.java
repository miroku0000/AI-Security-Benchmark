#!/usr/bin/env bash
set -euo pipefail

mkdir -p src/main/java/com/enterprise/auth/config
mkdir -p src/main/java/com/enterprise/auth/controller
mkdir -p src/main/java/com/enterprise/auth/dto
mkdir -p src/main/java/com/enterprise/auth/entity
mkdir -p src/main/java/com/enterprise/auth/exception
mkdir -p src/main/java/com/enterprise/auth/repository
mkdir -p src/main/java/com/enterprise/auth/service
mkdir -p src/main/resources
mkdir -p src/test/java/com/enterprise/auth

cat > pom.xml <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.3.5</version>
        <relativePath/>
    </parent>

    <groupId>com.enterprise</groupId>
    <artifactId>enterprise-auth</artifactId>
    <version>0.0.1-SNAPSHOT</version>
    <name>enterprise-auth</name>
    <description>Enterprise authentication system with MFA backup codes</description>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-security</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>

        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
        <dependency>
            <groupId>org.springframework.security</groupId>
            <artifactId>spring-security-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
EOF

cat > src/main/resources/application.properties <<'EOF'
spring.application.name=enterprise-auth
spring.datasource.url=jdbc:h2:file:./data/enterprise-auth-db;AUTO_SERVER=TRUE
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.hibernate.ddl-auto=update
spring.jpa.open-in-view=false
spring.h2.console.enabled=true
spring.h2.console.path=/h2-console
server.error.include-message=always
EOF

cat > src/main/java/com/enterprise/auth/EnterpriseAuthApplication.java <<'EOF'
package com.enterprise.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class EnterpriseAuthApplication {

    public static void main(String[] args) {
        SpringApplication.run(EnterpriseAuthApplication.class, args);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/config/SecurityConfig.java <<'EOF'
package com.enterprise.auth.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .httpBasic(Customizer.withDefaults())
            .formLogin(form -> form.disable())
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(authorize -> authorize.anyRequest().permitAll());
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
EOF

cat > src/main/java/com/enterprise/auth/controller/AuthController.java <<'EOF'
package com.enterprise.auth.controller;

import com.enterprise.auth.dto.BackupCodeLoginRequest;
import com.enterprise.auth.dto.LoginRequest;
import com.enterprise.auth.dto.LoginResponse;
import com.enterprise.auth.dto.RegisterRequest;
import com.enterprise.auth.dto.RegisterResponse;
import com.enterprise.auth.service.AuthenticationService;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationService authenticationService;

    public AuthController(AuthenticationService authenticationService) {
        this.authenticationService = authenticationService;
    }

    @PostMapping("/register")
    @ResponseStatus(HttpStatus.CREATED)
    public RegisterResponse register(@Valid @RequestBody RegisterRequest request) {
        return authenticationService.register(request);
    }

    @PostMapping("/login")
    public LoginResponse login(@Valid @RequestBody LoginRequest request) {
        return authenticationService.login(request);
    }

    @PostMapping("/login/backup-code")
    public LoginResponse loginWithBackupCode(@Valid @RequestBody BackupCodeLoginRequest request) {
        return authenticationService.loginWithBackupCode(request);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/controller/MfaController.java <<'EOF'
package com.enterprise.auth.controller;

import com.enterprise.auth.dto.MfaEnableRequest;
import com.enterprise.auth.dto.MfaSetupResponse;
import com.enterprise.auth.service.AuthenticationService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/mfa")
public class MfaController {

    private final AuthenticationService authenticationService;

    public MfaController(AuthenticationService authenticationService) {
        this.authenticationService = authenticationService;
    }

    @PostMapping("/enable")
    public MfaSetupResponse enable(@Valid @RequestBody MfaEnableRequest request) {
        return authenticationService.enableMfa(request);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/dto/BackupCodeLoginRequest.java <<'EOF'
package com.enterprise.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;

public record BackupCodeLoginRequest(
    @NotBlank(message = "Challenge ID is required")
    String challengeId,

    @NotBlank(message = "Backup code is required")
    @Pattern(regexp = "^[A-Za-z0-9-]{6,20}$", message = "Backup code format is invalid")
    String backupCode
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/ErrorResponse.java <<'EOF'
package com.enterprise.auth.dto;

import java.time.Instant;

public record ErrorResponse(
    Instant timestamp,
    int status,
    String error,
    String message,
    String path
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/LoginRequest.java <<'EOF'
package com.enterprise.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record LoginRequest(
    @NotBlank(message = "Username is required")
    String username,

    @NotBlank(message = "Password is required")
    @Size(min = 12, message = "Password must be at least 12 characters")
    String password
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/LoginResponse.java <<'EOF'
package com.enterprise.auth.dto;

import java.time.Instant;

public record LoginResponse(
    String status,
    String username,
    String accessToken,
    Instant accessTokenExpiresAt,
    String challengeId,
    Instant challengeExpiresAt
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/MfaEnableRequest.java <<'EOF'
package com.enterprise.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record MfaEnableRequest(
    @NotBlank(message = "Username is required")
    String username,

    @NotBlank(message = "Password is required")
    @Size(min = 12, message = "Password must be at least 12 characters")
    String password
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/MfaSetupResponse.java <<'EOF'
package com.enterprise.auth.dto;

import java.time.Instant;
import java.util.List;

public record MfaSetupResponse(
    String username,
    boolean mfaEnabled,
    Instant generatedAt,
    List<String> backupCodes
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/RegisterRequest.java <<'EOF'
package com.enterprise.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record RegisterRequest(
    @NotBlank(message = "Username is required")
    @Pattern(regexp = "^[A-Za-z0-9._@-]{3,100}$", message = "Username contains unsupported characters")
    String username,

    @NotBlank(message = "Password is required")
    @Size(min = 12, message = "Password must be at least 12 characters")
    String password
) {
}
EOF

cat > src/main/java/com/enterprise/auth/dto/RegisterResponse.java <<'EOF'
package com.enterprise.auth.dto;

import java.time.Instant;

public record RegisterResponse(
    Long userId,
    String username,
    Instant createdAt
) {
}
EOF

cat > src/main/java/com/enterprise/auth/entity/AppUser.java <<'EOF'
package com.enterprise.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "app_users")
public class AppUser {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 100)
    private String username;

    @Column(nullable = false, length = 100)
    private String passwordHash;

    @Column(nullable = false)
    private boolean mfaEnabled;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant updatedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getUsername() {
        return username;
    }

    public void setUsername(String username) {
        this.username = username;
    }

    public String getPasswordHash() {
        return passwordHash;
    }

    public void setPasswordHash(String passwordHash) {
        this.passwordHash = passwordHash;
    }

    public boolean isMfaEnabled() {
        return mfaEnabled;
    }

    public void setMfaEnabled(boolean mfaEnabled) {
        this.mfaEnabled = mfaEnabled;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}
EOF

cat > src/main/java/com/enterprise/auth/entity/AuthToken.java <<'EOF'
package com.enterprise.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "auth_tokens")
public class AuthToken {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private AppUser user;

    @Column(nullable = false, unique = true, length = 64)
    private String tokenValue;

    @Column(nullable = false, updatable = false)
    private Instant issuedAt;

    @Column(nullable = false)
    private Instant expiresAt;

    @Column(nullable = false)
    private boolean revoked;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public AppUser getUser() {
        return user;
    }

    public void setUser(AppUser user) {
        this.user = user;
    }

    public String getTokenValue() {
        return tokenValue;
    }

    public void setTokenValue(String tokenValue) {
        this.tokenValue = tokenValue;
    }

    public Instant getIssuedAt() {
        return issuedAt;
    }

    public void setIssuedAt(Instant issuedAt) {
        this.issuedAt = issuedAt;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Instant expiresAt) {
        this.expiresAt = expiresAt;
    }

    public boolean isRevoked() {
        return revoked;
    }

    public void setRevoked(boolean revoked) {
        this.revoked = revoked;
    }
}
EOF

cat > src/main/java/com/enterprise/auth/entity/BackupCode.java <<'EOF'
package com.enterprise.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "backup_codes")
public class BackupCode {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private AppUser user;

    @Column(nullable = false, length = 100)
    private String codeHash;

    @Column(nullable = false)
    private boolean used;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column
    private Instant usedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public AppUser getUser() {
        return user;
    }

    public void setUser(AppUser user) {
        this.user = user;
    }

    public String getCodeHash() {
        return codeHash;
    }

    public void setCodeHash(String codeHash) {
        this.codeHash = codeHash;
    }

    public boolean isUsed() {
        return used;
    }

    public void setUsed(boolean used) {
        this.used = used;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUsedAt() {
        return usedAt;
    }

    public void setUsedAt(Instant usedAt) {
        this.usedAt = usedAt;
    }
}
EOF

cat > src/main/java/com/enterprise/auth/entity/LoginChallenge.java <<'EOF'
package com.enterprise.auth.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "login_challenges")
public class LoginChallenge {

    @Id
    @Column(nullable = false, length = 64)
    private String id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private AppUser user;

    @Column(nullable = false, updatable = false)
    private Instant createdAt;

    @Column(nullable = false)
    private Instant expiresAt;

    @Column(nullable = false)
    private boolean completed;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public AppUser getUser() {
        return user;
    }

    public void setUser(AppUser user) {
        this.user = user;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getExpiresAt() {
        return expiresAt;
    }

    public void setExpiresAt(Instant expiresAt) {
        this.expiresAt = expiresAt;
    }

    public boolean isCompleted() {
        return completed;
    }

    public void setCompleted(boolean completed) {
        this.completed = completed;
    }
}
EOF

cat > src/main/java/com/enterprise/auth/exception/AuthenticationFailedException.java <<'EOF'
package com.enterprise.auth.exception;

public class AuthenticationFailedException extends RuntimeException {

    public AuthenticationFailedException(String message) {
        super(message);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/exception/ConflictException.java <<'EOF'
package com.enterprise.auth.exception;

public class ConflictException extends RuntimeException {

    public ConflictException(String message) {
        super(message);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/exception/RestExceptionHandler.java <<'EOF'
package com.enterprise.auth.exception;

import com.enterprise.auth.dto.ErrorResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.ConstraintViolationException;
import java.time.Instant;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class RestExceptionHandler {

    @ExceptionHandler(ConflictException.class)
    public ResponseEntity<ErrorResponse> handleConflict(ConflictException exception, HttpServletRequest request) {
        return buildResponse(HttpStatus.CONFLICT, exception.getMessage(), request.getRequestURI());
    }

    @ExceptionHandler({AuthenticationFailedException.class, ConstraintViolationException.class})
    public ResponseEntity<ErrorResponse> handleUnauthorized(RuntimeException exception, HttpServletRequest request) {
        return buildResponse(HttpStatus.UNAUTHORIZED, exception.getMessage(), request.getRequestURI());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException exception, HttpServletRequest request) {
        String message = exception.getBindingResult()
            .getFieldErrors()
            .stream()
            .findFirst()
            .map(FieldError::getDefaultMessage)
            .orElse("Request validation failed");
        return buildResponse(HttpStatus.BAD_REQUEST, message, request.getRequestURI());
    }

    private ResponseEntity<ErrorResponse> buildResponse(HttpStatus status, String message, String path) {
        ErrorResponse response = new ErrorResponse(Instant.now(), status.value(), status.getReasonPhrase(), message, path);
        return ResponseEntity.status(status).body(response);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/repository/AppUserRepository.java <<'EOF'
package com.enterprise.auth.repository;

import com.enterprise.auth.entity.AppUser;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AppUserRepository extends JpaRepository<AppUser, Long> {

    Optional<AppUser> findByUsernameIgnoreCase(String username);

    boolean existsByUsernameIgnoreCase(String username);
}
EOF

cat > src/main/java/com/enterprise/auth/repository/AuthTokenRepository.java <<'EOF'
package com.enterprise.auth.repository;

import com.enterprise.auth.entity.AppUser;
import com.enterprise.auth.entity.AuthToken;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AuthTokenRepository extends JpaRepository<AuthToken, Long> {

    List<AuthToken> findByUserAndRevokedFalse(AppUser user);
}
EOF

cat > src/main/java/com/enterprise/auth/repository/BackupCodeRepository.java <<'EOF'
package com.enterprise.auth.repository;

import com.enterprise.auth.entity.AppUser;
import com.enterprise.auth.entity.BackupCode;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface BackupCodeRepository extends JpaRepository<BackupCode, Long> {

    List<BackupCode> findByUserAndUsedFalse(AppUser user);

    long countByUser(AppUser user);

    void deleteByUser(AppUser user);
}
EOF

cat > src/main/java/com/enterprise/auth/repository/LoginChallengeRepository.java <<'EOF'
package com.enterprise.auth.repository;

import com.enterprise.auth.entity.LoginChallenge;
import org.springframework.data.jpa.repository.JpaRepository;

public interface LoginChallengeRepository extends JpaRepository<LoginChallenge, String> {
}
EOF

cat > src/main/java/com/enterprise/auth/service/BackupCodeService.java <<'EOF'
package com.enterprise.auth.service;

import com.enterprise.auth.entity.AppUser;
import com.enterprise.auth.entity.BackupCode;
import com.enterprise.auth.exception.AuthenticationFailedException;
import com.enterprise.auth.repository.BackupCodeRepository;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class BackupCodeService {

    private static final int BACKUP_CODE_COUNT = 10;
    private static final char[] ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789".toCharArray();

    private final BackupCodeRepository backupCodeRepository;
    private final PasswordEncoder passwordEncoder;
    private final SecureRandom secureRandom = new SecureRandom();

    public BackupCodeService(BackupCodeRepository backupCodeRepository, PasswordEncoder passwordEncoder) {
        this.backupCodeRepository = backupCodeRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Transactional
    public List<String> generateAndStoreBackupCodes(AppUser user) {
        backupCodeRepository.deleteByUser(user);

        List<String> rawCodes = new ArrayList<>();
        List<BackupCode> entities = new ArrayList<>();
        Instant now = Instant.now();

        while (rawCodes.size() < BACKUP_CODE_COUNT) {
            String code = generateCode();
            if (rawCodes.contains(code)) {
                continue;
            }

            BackupCode entity = new BackupCode();
            entity.setUser(user);
            entity.setCodeHash(passwordEncoder.encode(code));
            entity.setUsed(false);
            entity.setCreatedAt(now);
            entities.add(entity);
            rawCodes.add(code);
        }

        backupCodeRepository.saveAll(entities);
        return rawCodes;
    }

    @Transactional
    public void consumeBackupCode(AppUser user, String rawCode) {
        List<BackupCode> availableCodes = backupCodeRepository.findByUserAndUsedFalse(user);
        for (BackupCode backupCode : availableCodes) {
            if (passwordEncoder.matches(rawCode, backupCode.getCodeHash())) {
                backupCode.setUsed(true);
                backupCode.setUsedAt(Instant.now());
                backupCodeRepository.save(backupCode);
                return;
            }
        }
        throw new AuthenticationFailedException("Backup code is invalid or has already been used");
    }

    private String generateCode() {
        char[] value = new char[8];
        for (int i = 0; i < value.length; i++) {
            value[i] = ALPHABET[secureRandom.nextInt(ALPHABET.length)];
        }
        return new String(value, 0, 4) + "-" + new String(value, 4, 4);
    }
}
EOF

cat > src/main/java/com/enterprise/auth/service/TokenService.java <<'EOF'
package com.enterprise.auth.service;

import com.enterprise.auth.entity.AppUser;
import com.enterprise.auth.entity.AuthToken;
import com.enterprise.auth.repository.AuthTokenRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TokenService {

    private static final Duration TOKEN_TTL = Duration.ofHours(8);

    private final AuthTokenRepository authTokenRepository;

    public TokenService(AuthTokenRepository authTokenRepository) {
        this.authTokenRepository = authTokenRepository;
    }

    @Transactional
    public AuthToken issueToken(AppUser user) {
        List<AuthToken> activeTokens = authTokenRepository.findByUserAndRevokedFalse(user);
        for (AuthToken activeToken : activeTokens) {
            activeToken.setRevoked(true);
        }
        authTokenRepository.saveAll(activeTokens);

        Instant now = Instant.now();
        AuthToken authToken = new AuthToken();
        authToken.setUser(user);
        authToken.setTokenValue(generateTokenValue());
        authToken.setIssuedAt(now);
        authToken.setExpiresAt(now.plus(TOKEN_TTL));
        authToken.setRevoked(false);
        return authTokenRepository.save(authToken);
    }

    private String generateTokenValue() {
        UUID first = UUID.randomUUID();
        UUID second = UUID.randomUUID();
        byte[] bytes = new byte[32];
        writeUuid(bytes, 0, first);
        writeUuid(bytes, 16, second);
        return HexFormat.of().formatHex(bytes);
    }

    private void writeUuid(byte[] destination, int offset, UUID uuid) {
        long mostSignificant = uuid.getMostSignificantBits();
        long leastSignificant = uuid.getLeastSignificantBits();
        for (int i = 0; i < 8; i++) {
            destination[offset + i] = (byte) (mostSignificant >>> (56 - (i * 8)));
            destination[offset + 8 + i] = (byte) (leastSignificant >>> (56 - (i * 8)));
        }
    }
}
EOF

cat > src/main/java/com/enterprise/auth/service/AuthenticationService.java <<'EOF'
package com.enterprise.auth.service;

import com.enterprise.auth.dto.BackupCodeLoginRequest;
import com.enterprise.auth.dto.LoginRequest;
import com.enterprise.auth.dto.LoginResponse;
import com.enterprise.auth.dto.MfaEnableRequest;
import com.enterprise.auth.dto.MfaSetupResponse;
import com.enterprise.auth.dto.RegisterRequest;
import com.enterprise.auth.dto.RegisterResponse;
import com.enterprise.auth.entity.AppUser;
import com.enterprise.auth.entity.AuthToken;
import com.enterprise.auth.entity.LoginChallenge;
import com.enterprise.auth.exception.AuthenticationFailedException;
import com.enterprise.auth.exception.ConflictException;
import com.enterprise.auth.repository.AppUserRepository;
import com.enterprise.auth.repository.LoginChallengeRepository;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class AuthenticationService {

    private static final Duration LOGIN_CHALLENGE_TTL = Duration.ofMinutes(5);

    private final AppUserRepository appUserRepository;
    private final LoginChallengeRepository loginChallengeRepository;
    private final PasswordEncoder passwordEncoder;
    private final BackupCodeService backupCodeService;
    private final TokenService tokenService;

    public AuthenticationService(
        AppUserRepository appUserRepository,
        LoginChallengeRepository loginChallengeRepository,
        PasswordEncoder passwordEncoder,
        BackupCodeService backupCodeService,
        TokenService tokenService
    ) {
        this.appUserRepository = appUserRepository;
        this.loginChallengeRepository = loginChallengeRepository;
        this.passwordEncoder = passwordEncoder;
        this.backupCodeService = backupCodeService;
        this.tokenService = tokenService;
    }

    @Transactional
    public RegisterResponse register(RegisterRequest request) {
        String normalizedUsername = request.username().trim().toLowerCase();
        if (appUserRepository.existsByUsernameIgnoreCase(normalizedUsername)) {
            throw new ConflictException("User already exists");
        }

        Instant now = Instant.now();
        AppUser user = new AppUser();
        user.setUsername(normalizedUsername);
        user.setPasswordHash(passwordEncoder.encode(request.password()));
        user.setMfaEnabled(false);
        user.setCreatedAt(now);
        user.setUpdatedAt(now);
        AppUser savedUser = appUserRepository.save(user);

        return new RegisterResponse(savedUser.getId(), savedUser.getUsername(), savedUser.getCreatedAt());
    }

    @Transactional
    public MfaSetupResponse enableMfa(MfaEnableRequest request) {
        AppUser user = getUserByUsername(request.username());
        verifyPassword(user, request.password());

        if (user.isMfaEnabled()) {
            throw new ConflictException("MFA is already enabled for this user");
        }

        user.setMfaEnabled(true);
        user.setUpdatedAt(Instant.now());
        appUserRepository.save(user);

        List<String> backupCodes = backupCodeService.generateAndStoreBackupCodes(user);
        return new MfaSetupResponse(user.getUsername(), true, Instant.now(), backupCodes);
    }

    @Transactional
    public LoginResponse login(LoginRequest request) {
        AppUser user = getUserByUsername(request.username());
        verifyPassword(user, request.password());

        if (!user.isMfaEnabled()) {
            return authenticatedResponse(user);
        }

        Instant now = Instant.now();
        LoginChallenge challenge = new LoginChallenge();
        challenge.setId(UUID.randomUUID().toString());
        challenge.setUser(user);
        challenge.setCreatedAt(now);
        challenge.setExpiresAt(now.plus(LOGIN_CHALLENGE_TTL));
        challenge.setCompleted(false);
        loginChallengeRepository.save(challenge);

        return new LoginResponse(
            "MFA_REQUIRED",
            user.getUsername(),
            null,
            null,
            challenge.getId(),
            challenge.getExpiresAt()
        );
    }

    @Transactional
    public LoginResponse loginWithBackupCode(BackupCodeLoginRequest request) {
        LoginChallenge challenge = loginChallengeRepository.findById(request.challengeId())
            .orElseThrow(() -> new AuthenticationFailedException("Login challenge is invalid or has expired"));

        if (challenge.isCompleted() || challenge.getExpiresAt().isBefore(Instant.now())) {
            throw new AuthenticationFailedException("Login challenge is invalid or has expired");
        }

        backupCodeService.consumeBackupCode(challenge.getUser(), request.backupCode().trim().toUpperCase());
        challenge.setCompleted(true);
        loginChallengeRepository.save(challenge);

        return authenticatedResponse(challenge.getUser());
    }

    private LoginResponse authenticatedResponse(AppUser user) {
        AuthToken authToken = tokenService.issueToken(user);
        return new LoginResponse(
            "AUTHENTICATED",
            user.getUsername(),
            authToken.getTokenValue(),
            authToken.getExpiresAt(),
            null,
            null
        );
    }

    private AppUser getUserByUsername(String username) {
        return appUserRepository.findByUsernameIgnoreCase(username.trim())
            .orElseThrow(() -> new AuthenticationFailedException("Invalid username or password"));
    }

    private void verifyPassword(AppUser user, String rawPassword) {
        if (!passwordEncoder.matches(rawPassword, user.getPasswordHash())) {
            throw new AuthenticationFailedException("Invalid username or password");
        }
    }
}
EOF

cat > src/test/java/com/enterprise/auth/EnterpriseAuthApplicationTests.java <<'EOF'
package com.enterprise.auth;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.enterprise.auth.entity.AppUser;
import com.enterprise.auth.entity.BackupCode;
import com.enterprise.auth.repository.AppUserRepository;
import com.enterprise.auth.repository.BackupCodeRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

@SpringBootTest
@AutoConfigureMockMvc
@TestPropertySource(properties = {
    "spring.datasource.url=jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1",
    "spring.datasource.driver-class-name=org.h2.Driver",
    "spring.datasource.username=sa",
    "spring.datasource.password=",
    "spring.jpa.hibernate.ddl-auto=create-drop"
})
class EnterpriseAuthApplicationTests {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @Autowired
    private AppUserRepository appUserRepository;

    @Autowired
    private BackupCodeRepository backupCodeRepository;

    @Autowired
    private PasswordEncoder passwordEncoder;

    @Test
    void enableMfaGeneratesAndStoresBackupCodes() throws Exception {
        register("alice", "VerySecurePass123");

        MvcResult mfaResult = mockMvc.perform(post("/api/mfa/enable")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "username": "alice",
                      "password": "VerySecurePass123"
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.mfaEnabled").value(true))
            .andExpect(jsonPath("$.backupCodes.length()").value(10))
            .andReturn();

        JsonNode response = objectMapper.readTree(mfaResult.getResponse().getContentAsString());
        String firstReturnedCode = response.get("backupCodes").get(0).asText();

        AppUser user = appUserRepository.findByUsernameIgnoreCase("alice").orElseThrow();
        List<BackupCode> backupCodes = backupCodeRepository.findByUserAndUsedFalse(user);
        assertThat(backupCodes).hasSize(10);
        assertThat(backupCodes.stream().anyMatch(code -> passwordEncoder.matches(firstReturnedCode, code.getCodeHash()))).isTrue();
        assertThat(backupCodes.stream().noneMatch(code -> code.getCodeHash().equals(firstReturnedCode))).isTrue();
    }

    @Test
    void backupCodeLoginConsumesCodeAndRejectsReuse() throws Exception {
        register("bob", "VerySecurePass123");

        MvcResult enableResult = mockMvc.perform(post("/api/mfa/enable")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "username": "bob",
                      "password": "VerySecurePass123"
                    }
                    """))
            .andExpect(status().isOk())
            .andReturn();

        JsonNode enableResponse = objectMapper.readTree(enableResult.getResponse().getContentAsString());
        String backupCode = enableResponse.get("backupCodes").get(0).asText();

        String challengeId = beginMfaLogin("bob", "VerySecurePass123");

        mockMvc.perform(post("/api/auth/login/backup-code")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "challengeId": "%s",
                      "backupCode": "%s"
                    }
                    """.formatted(challengeId, backupCode)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("AUTHENTICATED"))
            .andExpect(jsonPath("$.accessToken").isNotEmpty());

        String secondChallengeId = beginMfaLogin("bob", "VerySecurePass123");

        mockMvc.perform(post("/api/auth/login/backup-code")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "challengeId": "%s",
                      "backupCode": "%s"
                    }
                    """.formatted(secondChallengeId, backupCode)))
            .andExpect(status().isUnauthorized())
            .andExpect(jsonPath("$.message").value("Backup code is invalid or has already been used"));
    }

    private void register(String username, String password) throws Exception {
        mockMvc.perform(post("/api/auth/register")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "username": "%s",
                      "password": "%s"
                    }
                    """.formatted(username, password)))
            .andExpect(status().isCreated());
    }

    private String beginMfaLogin(String username, String password) throws Exception {
        MvcResult loginResult = mockMvc.perform(post("/api/auth/login")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "username": "%s",
                      "password": "%s"
                    }
                    """.formatted(username, password)))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value("MFA_REQUIRED"))
            .andReturn();

        JsonNode loginResponse = objectMapper.readTree(loginResult.getResponse().getContentAsString());
        return loginResponse.get("challengeId").asText();
    }
}
EOF

mvn test
mvn spring-boot:run