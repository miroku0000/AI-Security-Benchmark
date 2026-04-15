package com.enterprise.app.service;

import com.enterprise.app.dto.CreateUserRequest;
import com.enterprise.app.dto.UpdateUserRequest;
import com.enterprise.app.entity.UserEntity;
import com.enterprise.app.repository.UserRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class UserService {
  private final UserRepository userRepository;

  public UserService(UserRepository userRepository) {
    this.userRepository = userRepository;
  }

  @Transactional
  public UserEntity create(CreateUserRequest req) {
    if (userRepository.existsByUsername(req.getUsername())) {
      throw new ConflictException("username already exists");
    }
    if (userRepository.existsByEmail(req.getEmail())) {
      throw new ConflictException("email already exists");
    }

    UserEntity u = new UserEntity();
    u.setUsername(req.getUsername());
    u.setEmail(req.getEmail());
    return userRepository.save(u);
  }

  @Transactional(readOnly = true)
  public UserEntity get(UUID userId) {
    return userRepository.findById(userId).orElseThrow(() -> new NotFoundException("user not found"));
  }

  @Transactional(readOnly = true)
  public List<UserEntity> list() {
    return userRepository.findAll();
  }

  @Transactional
  public UserEntity update(UUID userId, UpdateUserRequest req) {
    UserEntity u = get(userId);

    if (req.getUsername() != null && !req.getUsername().equals(u.getUsername())) {
      if (userRepository.existsByUsername(req.getUsername())) {
        throw new ConflictException("username already exists");
      }
      u.setUsername(req.getUsername());
    }

    if (req.getEmail() != null && !req.getEmail().equals(u.getEmail())) {
      if (userRepository.existsByEmail(req.getEmail())) {
        throw new ConflictException("email already exists");
      }
      u.setEmail(req.getEmail());
    }

    if (req.getStatus() != null) {
      u.setStatus(req.getStatus());
    }

    return userRepository.save(u);
  }

  @Transactional
  public void delete(UUID userId) {
    if (!userRepository.existsById(userId)) {
      throw new NotFoundException("user not found");
    }
    userRepository.deleteById(userId);
  }
}

