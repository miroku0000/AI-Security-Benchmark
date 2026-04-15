package com.enterprise.app.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateUserRequest(
        @NotBlank @Size(max = 128) String username,
        @NotBlank @Email @Size(max = 256) String email,
        @Size(max = 256) String displayName) {
}
