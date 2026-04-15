package com.example.mfa.repo;

import com.example.mfa.model.BackupCode;
import com.example.mfa.model.User;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface BackupCodeRepository extends JpaRepository<BackupCode, Long> {

  List<BackupCode> findByUserAndUsedFalse(User user);

  @Modifying
  @Query("delete from BackupCode b where b.user = :user")
  void deleteByUser(@Param("user") User user);
}
