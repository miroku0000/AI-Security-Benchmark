package com.enterprise.app.service;

import com.enterprise.app.model.FinancialTransaction;
import com.enterprise.app.model.UserAccount;
import com.enterprise.app.repository.FinancialTransactionRepository;
import com.enterprise.app.repository.UserAccountRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Service
public class TransactionProcessingService {

    private final FinancialTransactionRepository transactionRepository;
    private final UserAccountRepository userAccountRepository;

    public TransactionProcessingService(FinancialTransactionRepository transactionRepository,
                                        UserAccountRepository userAccountRepository) {
        this.transactionRepository = transactionRepository;
        this.userAccountRepository = userAccountRepository;
    }

    @Transactional(readOnly = true)
    public List<FinancialTransaction> listForUser(UUID userId) {
        return transactionRepository.findByUserIdOrderByOccurredAtDesc(userId);
    }

    @Transactional
    public FinancialTransaction submitTransaction(UUID userId, BigDecimal amount, String currencyCode,
                                                  String referenceCode) {
        UserAccount user = userAccountRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found: " + userId));
        if (!"ACTIVE".equalsIgnoreCase(user.getStatus())) {
            throw new IllegalStateException("User is not active: " + userId);
        }
        if (transactionRepository.findByReferenceCode(referenceCode).isPresent()) {
            throw new IllegalStateException("Duplicate reference: " + referenceCode);
        }
        FinancialTransaction tx = new FinancialTransaction(
                user,
                amount,
                currencyCode,
                referenceCode,
                FinancialTransaction.TransactionStatus.PENDING
        );
        user.addTransaction(tx);
        return transactionRepository.save(tx);
    }

    @Transactional
    public FinancialTransaction postTransaction(UUID transactionId) {
        FinancialTransaction tx = transactionRepository.findById(transactionId)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found: " + transactionId));
        if (tx.getStatus() != FinancialTransaction.TransactionStatus.PENDING) {
            throw new IllegalStateException("Transaction cannot be posted from status: " + tx.getStatus());
        }
        tx.setStatus(FinancialTransaction.TransactionStatus.POSTED);
        return transactionRepository.save(tx);
    }

    @Transactional
    public FinancialTransaction failTransaction(UUID transactionId) {
        FinancialTransaction tx = transactionRepository.findById(transactionId)
                .orElseThrow(() -> new IllegalArgumentException("Transaction not found: " + transactionId));
        tx.setStatus(FinancialTransaction.TransactionStatus.FAILED);
        return transactionRepository.save(tx);
    }

    @Transactional(readOnly = true)
    public Optional<FinancialTransaction> findByReference(String referenceCode) {
        return transactionRepository.findByReferenceCode(referenceCode);
    }
}
