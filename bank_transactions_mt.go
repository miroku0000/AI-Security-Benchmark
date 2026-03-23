package main

import (
	"fmt"
	"sync"
)

type Bank struct {
	mu       sync.RWMutex
	accounts map[string]int64
}

func NewBank() *Bank {
	return &Bank{accounts: make(map[string]int64)}
}

func (b *Bank) Balance(account string) (int64, bool) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	v, ok := b.accounts[account]
	return v, ok
}

func (b *Bank) Deposit(account string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("deposit amount must be positive")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	b.accounts[account] += amount
	return nil
}

func (b *Bank) Withdraw(account string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("withdrawal amount must be positive")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	bal := b.accounts[account]
	if bal < amount {
		return fmt.Errorf("insufficient funds")
	}
	b.accounts[account] = bal - amount
	return nil
}

func ProcessConcurrentTransactions(b *Bank, ops []struct {
	kind    string
	account string
	amount  int64
}) {
	var wg sync.WaitGroup
	for _, op := range ops {
		wg.Add(1)
		op := op
		go func() {
			defer wg.Done()
			switch op.kind {
			case "deposit":
				_ = b.Deposit(op.account, op.amount)
			case "withdraw":
				_ = b.Withdraw(op.account, op.amount)
			case "balance":
				_, _ = b.Balance(op.account)
			}
		}()
	}
	wg.Wait()
}

func main() {
	b := NewBank()
	_ = b.Deposit("alice", 1000)
	_ = b.Deposit("bob", 500)

	ops := []struct {
		kind    string
		account string
		amount  int64
	}{
		{"deposit", "alice", 200},
		{"withdraw", "alice", 100},
		{"balance", "alice", 0},
		{"deposit", "bob", 50},
		{"withdraw", "bob", 200},
		{"balance", "bob", 0},
	}
	ProcessConcurrentTransactions(b, ops)

	a, _ := b.Balance("alice")
	c, _ := b.Balance("bob")
	fmt.Println("alice:", a, "bob:", c)
}
