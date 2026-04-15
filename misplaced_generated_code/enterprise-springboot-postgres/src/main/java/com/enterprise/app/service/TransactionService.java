package com.enterprise.app.service;

import com.enterprise.app.dto.CreateTransactionRequest;
import com.enterprise.app.entity.AccountTransactionEntity;
import com.enterprise.app.entity.UserEntity;
import com.enterprise.app.repository.AccountTransactionRepository;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TransactionService {
  private final AccountTransactionRepository transactionRepository;
  private final UserService userService;

  public TransactionService(AccountTransactionRepository transactionRepository, UserService userService) {
    this.transactionRepository = transactionRepository;
    this.userService = userService;
  }

  @Transactional
  public AccountTransactionEntity create(UUID userId, CreateTransactionRequest req) {
    UserEntity user = userService.get(userId);

    AccountTransactionEntity tx = new AccountTransactionEntity();
    tx.setUser(user);
    tx.setAmount(req.getAmount());
    tx.setCurrency(req.getCurrency().toUpperCase());
    tx.setType(req.getType());
    tx.setReference(req.getReference());
    return transactionRepository.save(tx);
  }

  @Transactional(readOnly = true)
  public List<AccountTransactionEntity> listForUser(UUID userId) {
    userService.get(userId);
    return transactionRepository.findByUserIdOrderByCreatedAtDesc(userId);
  }
}

