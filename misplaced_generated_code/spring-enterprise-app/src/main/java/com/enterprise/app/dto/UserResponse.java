package com.enterprise.app.dto;

import com.enterprise.app.model.User;

import java.time.Instant;

public record UserResponse(
        Long id,
        String username,
        String email,
        String displayName,
        boolean active,
        Instant createdAt) {

    public static UserResponse from(User u) {
        return new UserResponse(
                u.getId(),
                u.getUsername(),
                u.getEmail(),
                u.getDisplayName(),
                u.isActive(),
                u.getCreatedAt());
    }
}
