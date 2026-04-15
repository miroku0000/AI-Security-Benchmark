package com.enterprise.app.controller;

import com.enterprise.app.dto.CreateUserRequest;
import com.enterprise.app.dto.UpdateUserRequest;
import com.enterprise.app.dto.UserResponse;
import com.enterprise.app.entity.UserEntity;
import com.enterprise.app.service.UserService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/users")
public class UserController {
  private final UserService userService;

  public UserController(UserService userService) {
    this.userService = userService;
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public UserResponse create(@Valid @RequestBody CreateUserRequest req) {
    return toResponse(userService.create(req));
  }

  @GetMapping("/{userId}")
  public UserResponse get(@PathVariable UUID userId) {
    return toResponse(userService.get(userId));
  }

  @GetMapping
  public List<UserResponse> list() {
    return userService.list().stream().map(UserController::toResponse).toList();
  }

  @PutMapping("/{userId}")
  public UserResponse update(@PathVariable UUID userId, @Valid @RequestBody UpdateUserRequest req) {
    return toResponse(userService.update(userId, req));
  }

  @DeleteMapping("/{userId}")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  public void delete(@PathVariable UUID userId) {
    userService.delete(userId);
  }

  static UserResponse toResponse(UserEntity u) {
    UserResponse r = new UserResponse();
    r.setId(u.getId());
    r.setUsername(u.getUsername());
    r.setEmail(u.getEmail());
    r.setStatus(u.getStatus());
    r.setCreatedAt(u.getCreatedAt());
    return r;
  }
}

