package com.enterprise.app.service;

import com.enterprise.app.model.UserAccount;
import com.enterprise.app.repository.UserAccountRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class UserManagementService {

    private final UserAccountRepository userAccountRepository;

    public UserManagementService(UserAccountRepository userAccountRepository) {
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional(readOnly = true)
    public Optional<UserAccount> findById(UUID id) {
        return userAccountRepository.findById(id);
    }

    @Transactional(readOnly = true)
    public Optional<UserAccount> findByEmail(String email) {
        return userAccountRepository.findByEmailIgnoreCase(email);
    }

    @Transactional
    public UserAccount registerUser(String email, String displayName) {
        if (userAccountRepository.existsByEmailIgnoreCase(email)) {
            throw new IllegalStateException("User already exists: " + email);
        }
        UserAccount user = new UserAccount(email, displayName, "ACTIVE");
        return userAccountRepository.save(user);
    }

    @Transactional
    public UserAccount updateDisplayName(UUID userId, String displayName) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        user.setDisplayName(displayName);
        user.setUpdatedAt(Instant.now());
        return userAccountRepository.save(user);
    }

    @Transactional
    public void deactivateUser(UUID userId) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        user.setStatus("INACTIVE");
        user.setUpdatedAt(Instant.now());
        userAccountRepository.save(user);
    }

    @Transactional(readOnly = true)
    public List<UserAccount> listActiveUsers() {
        return userAccountRepository.findByStatusOrderByCreatedAtDesc("ACTIVE");
    }
}
