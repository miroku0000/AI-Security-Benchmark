package com.enterprise.app.repository;

import com.enterprise.app.model.FinancialTransaction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface FinancialTransactionRepository extends JpaRepository<FinancialTransaction, UUID> {

    List<FinancialTransaction> findByUserIdOrderByOccurredAtDesc(UUID userId);

    Optional<FinancialTransaction> findByReferenceCode(String referenceCode);

    @Query("select t from FinancialTransaction t join fetch t.user u where t.id = :id")
    Optional<FinancialTransaction> findByIdWithUser(@Param("id") UUID id);

    List<FinancialTransaction> findByStatus(FinancialTransaction.TransactionStatus status);
}
