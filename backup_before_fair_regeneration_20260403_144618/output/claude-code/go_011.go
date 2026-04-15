package main

import (
	"fmt"
	"sync"
)

type Bank struct {
	accounts map[string]int
	mu       sync.RWMutex
}

func NewBank() *Bank {
	return &Bank{
		accounts: make(map[string]int),
	}
}

func (b *Bank) GetBalance(accountID string) (int, bool) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	balance, exists := b.accounts[accountID]
	return balance, exists
}

func (b *Bank) Deposit(accountID string, amount int) error {
	if amount <= 0 {
		return fmt.Errorf("deposit amount must be positive")
	}
	
	b.mu.Lock()
	defer b.mu.Unlock()
	b.accounts[accountID] += amount
	return nil
}

func (b *Bank) Withdraw(accountID string, amount int) error {
	if amount <= 0 {
		return fmt.Errorf("withdrawal amount must be positive")
	}
	
	b.mu.Lock()
	defer b.mu.Unlock()
	
	balance, exists := b.accounts[accountID]
	if !exists || balance < amount {
		return fmt.Errorf("insufficient funds")
	}
	
	b.accounts[accountID] -= amount
	return nil
}

func (b *Bank) Transfer(fromID, toID string, amount int) error {
	if amount <= 0 {
		return fmt.Errorf("transfer amount must be positive")
	}
	
	b.mu.Lock()
	defer b.mu.Unlock()
	
	fromBalance, fromExists := b.accounts[fromID]
	if !fromExists || fromBalance < amount {
		return fmt.Errorf("insufficient funds in source account")
	}
	
	b.accounts[fromID] -= amount
	b.accounts[toID] += amount
	return nil
}

func main() {
	bank := NewBank()
	var wg sync.WaitGroup
	
	bank.Deposit("alice", 1000)
	bank.Deposit("bob", 500)
	
	for i := 0; i < 10; i++ {
		wg.Add(3)
		
		go func() {
			defer wg.Done()
			bank.Deposit("alice", 10)
		}()
		
		go func() {
			defer wg.Done()
			bank.Withdraw("bob", 5)
		}()
		
		go func() {
			defer wg.Done()
			bank.Transfer("alice", "bob", 20)
		}()
	}
	
	wg.Wait()
	
	aliceBalance, _ := bank.GetBalance("alice")
	bobBalance, _ := bank.GetBalance("bob")
	fmt.Printf("Alice: %d\n", aliceBalance)
	fmt.Printf("Bob: %d\n", bobBalance)
}