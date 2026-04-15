package com.enterprise.app.repository;

import com.enterprise.app.model.UserAccount;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface UserAccountRepository extends JpaRepository<UserAccount, UUID> {

    Optional<UserAccount> findByEmailIgnoreCase(String email);

    boolean existsByEmailIgnoreCase(String email);

    @Query("select distinct u from UserAccount u left join fetch u.transactions t where u.id = :id")
    Optional<UserAccount> findByIdWithTransactions(@Param("id") UUID id);

    List<UserAccount> findByStatusOrderByCreatedAtDesc(String status);
}
