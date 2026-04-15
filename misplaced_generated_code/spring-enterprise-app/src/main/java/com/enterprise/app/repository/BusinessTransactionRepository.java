package com.enterprise.app.repository;

import com.enterprise.app.model.BusinessTransaction;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface BusinessTransactionRepository extends JpaRepository<BusinessTransaction, Long> {

    @EntityGraph(attributePaths = "user")
    @Override
    Optional<BusinessTransaction> findById(Long id);

    @EntityGraph(attributePaths = "user")
    Optional<BusinessTransaction> findByReference(String reference);

    @EntityGraph(attributePaths = "user")
    List<BusinessTransaction> findByUserIdOrderByCreatedAtDesc(Long userId);

    List<BusinessTransaction> findByUserIdAndStatus(Long userId, BusinessTransaction.Status status);
}
