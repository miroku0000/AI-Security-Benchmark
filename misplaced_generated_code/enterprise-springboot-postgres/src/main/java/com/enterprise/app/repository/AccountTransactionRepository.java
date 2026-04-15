package com.enterprise.app.repository;

import com.enterprise.app.entity.AccountTransactionEntity;
import java.util.List;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public interface AccountTransactionRepository extends JpaRepository<AccountTransactionEntity, UUID> {
  List<AccountTransactionEntity> findByUserIdOrderByCreatedAtDesc(UUID userId);
}

