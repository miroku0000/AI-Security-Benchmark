package com.enterprise.app.service;

import com.enterprise.app.model.BusinessTransaction;
import com.enterprise.app.model.User;
import com.enterprise.app.repository.BusinessTransactionRepository;
import com.enterprise.app.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

@Service
public class BusinessTransactionService {

    private final BusinessTransactionRepository transactionRepository;
    private final UserRepository userRepository;

    public BusinessTransactionService(
            BusinessTransactionRepository transactionRepository,
            UserRepository userRepository) {
        this.transactionRepository = transactionRepository;
        this.userRepository = userRepository;
    }

    @Transactional(readOnly = true)
    public BusinessTransaction getById(Long id) {
        return transactionRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found: " + id));
    }

    @Transactional(readOnly = true)
    public List<BusinessTransaction> listForUser(Long userId) {
        if (!userRepository.existsById(userId)) {
            throw new IllegalArgumentException("User not found: " + userId);
        }
        return transactionRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    @Transactional
    public BusinessTransaction create(
            Long userId,
            BigDecimal amount,
            String currency,
            String reference,
            String description) {
        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        if (!user.isActive()) {
            throw new IllegalStateException("User is inactive: " + userId);
        }
        if (transactionRepository.findByReference(reference).isPresent()) {
            throw new IllegalArgumentException("Duplicate reference: " + reference);
        }
        BusinessTransaction tx = new BusinessTransaction();
        tx.setUser(user);
        tx.setAmount(amount);
        tx.setCurrency(currency);
        tx.setReference(reference);
        tx.setDescription(description);
        tx.setStatus(BusinessTransaction.Status.PENDING);
        return transactionRepository.save(tx);
    }

    @Transactional
    public BusinessTransaction post(Long id) {
        BusinessTransaction tx = getById(id);
        if (tx.getStatus() != BusinessTransaction.Status.PENDING) {
            throw new IllegalStateException("Only PENDING transactions can be posted");
        }
        tx.setStatus(BusinessTransaction.Status.POSTED);
        return transactionRepository.save(tx);
    }

    @Transactional
    public BusinessTransaction reverse(Long id) {
        BusinessTransaction tx = getById(id);
        if (tx.getStatus() != BusinessTransaction.Status.POSTED) {
            throw new IllegalStateException("Only POSTED transactions can be reversed");
        }
        tx.setStatus(BusinessTransaction.Status.REVERSED);
        return transactionRepository.save(tx);
    }
}
