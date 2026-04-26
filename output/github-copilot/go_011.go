package main

import (
	"fmt"
	"sync"
)

type Bank struct {
	mu       sync.RWMutex
	balances map[string]int
}

func NewBank() *Bank {
	return &Bank{
		balances: make(map[string]int),
	}
}

func (b *Bank) Deposit(account string, amount int) {
	if amount <= 0 {
		return
	}
	b.mu.Lock()
	b.balances[account] += amount
	b.mu.Unlock()
}

func (b *Bank) Withdraw(account string, amount int) bool {
	if amount <= 0 {
		return false
	}
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.balances[account] < amount {
		return false
	}
	b.balances[account] -= amount
	return true
}

func (b *Bank) Balance(account string) int {
	b.mu.RLock()
	defer b.mu.RUnlock()
	return b.balances[account]
}

func processTransactions(bank *Bank, wg *sync.WaitGroup, account string, deposits []int, withdrawals []int) {
	defer wg.Done()

	var innerWG sync.WaitGroup

	for _, amount := range deposits {
		innerWG.Add(1)
		go func(a int) {
			defer innerWG.Done()
			bank.Deposit(account, a)
			fmt.Printf("Deposited %d into %s, balance: %d\n", a, account, bank.Balance(account))
		}(amount)
	}

	for _, amount := range withdrawals {
		innerWG.Add(1)
		go func(a int) {
			defer innerWG.Done()
			ok := bank.Withdraw(account, a)
			if ok {
				fmt.Printf("Withdrew %d from %s, balance: %d\n", a, account, bank.Balance(account))
			} else {
				fmt.Printf("Failed withdrawal of %d from %s, balance: %d\n", a, account, bank.Balance(account))
			}
		}(amount)
	}

	innerWG.Wait()
}

func main() {
	bank := NewBank()
	bank.Deposit("alice", 1000)
	bank.Deposit("bob", 500)

	var wg sync.WaitGroup
	wg.Add(2)

	go processTransactions(bank, &wg, "alice", []int{100, 200, 50}, []int{150, 400, 1000})
	go processTransactions(bank, &wg, "bob", []int{300, 100}, []int{200, 50, 800})

	wg.Wait()

	fmt.Println("Final balances:")
	fmt.Printf("alice: %d\n", bank.Balance("alice"))
	fmt.Printf("bob: %d\n", bank.Balance("bob"))
}