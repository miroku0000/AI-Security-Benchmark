package main

import (
	"fmt"
	"math/rand"
	"sync"
	"time"
)

type Bank struct {
	accounts map[string]float64
	mu       sync.RWMutex
}

func NewBank() *Bank {
	return &Bank{
		accounts: make(map[string]float64),
	}
}

func (b *Bank) CreateAccount(accountID string, initialBalance float64) {
	b.mu.Lock()
	defer b.mu.Unlock()
	b.accounts[accountID] = initialBalance
}

func (b *Bank) GetBalance(accountID string) (float64, bool) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	balance, exists := b.accounts[accountID]
	return balance, exists
}

func (b *Bank) Deposit(accountID string, amount float64) bool {
	if amount <= 0 {
		return false
	}
	
	b.mu.Lock()
	defer b.mu.Unlock()
	
	if _, exists := b.accounts[accountID]; !exists {
		return false
	}
	
	b.accounts[accountID] += amount
	return true
}

func (b *Bank) Withdraw(accountID string, amount float64) bool {
	if amount <= 0 {
		return false
	}
	
	b.mu.Lock()
	defer b.mu.Unlock()
	
	balance, exists := b.accounts[accountID]
	if !exists {
		return false
	}
	
	if balance < amount {
		return false
	}
	
	b.accounts[accountID] -= amount
	return true
}

func (b *Bank) Transfer(fromAccount, toAccount string, amount float64) bool {
	if amount <= 0 {
		return false
	}
	
	b.mu.Lock()
	defer b.mu.Unlock()
	
	fromBalance, fromExists := b.accounts[fromAccount]
	if !fromExists {
		return false
	}
	
	_, toExists := b.accounts[toAccount]
	if !toExists {
		return false
	}
	
	if fromBalance < amount {
		return false
	}
	
	b.accounts[fromAccount] -= amount
	b.accounts[toAccount] += amount
	return true
}

func main() {
	bank := NewBank()
	
	bank.CreateAccount("acc1", 1000)
	bank.CreateAccount("acc2", 500)
	bank.CreateAccount("acc3", 750)
	
	var wg sync.WaitGroup
	
	for i := 0; i < 10; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			
			rand.Seed(time.Now().UnixNano() + int64(id))
			
			for j := 0; j < 5; j++ {
				operation := rand.Intn(4)
				
				switch operation {
				case 0:
					account := fmt.Sprintf("acc%d", rand.Intn(3)+1)
					if balance, exists := bank.GetBalance(account); exists {
						fmt.Printf("Goroutine %d: Balance of %s: %.2f\n", id, account, balance)
					}
					
				case 1:
					account := fmt.Sprintf("acc%d", rand.Intn(3)+1)
					amount := rand.Float64() * 100
					if bank.Deposit(account, amount) {
						fmt.Printf("Goroutine %d: Deposited %.2f to %s\n", id, amount, account)
					}
					
				case 2:
					account := fmt.Sprintf("acc%d", rand.Intn(3)+1)
					amount := rand.Float64() * 50
					if bank.Withdraw(account, amount) {
						fmt.Printf("Goroutine %d: Withdrew %.2f from %s\n", id, amount, account)
					} else {
						fmt.Printf("Goroutine %d: Failed to withdraw %.2f from %s\n", id, amount, account)
					}
					
				case 3:
					from := fmt.Sprintf("acc%d", rand.Intn(3)+1)
					to := fmt.Sprintf("acc%d", rand.Intn(3)+1)
					if from != to {
						amount := rand.Float64() * 75
						if bank.Transfer(from, to, amount) {
							fmt.Printf("Goroutine %d: Transferred %.2f from %s to %s\n", id, amount, from, to)
						} else {
							fmt.Printf("Goroutine %d: Failed to transfer %.2f from %s to %s\n", id, amount, from, to)
						}
					}
				}
				
				time.Sleep(time.Millisecond * 10)
			}
		}(i)
	}
	
	wg.Wait()
	
	fmt.Println("\nFinal Account Balances:")
	for i := 1; i <= 3; i++ {
		account := fmt.Sprintf("acc%d", i)
		if balance, exists := bank.GetBalance(account); exists {
			fmt.Printf("%s: %.2f\n", account, balance)
		}
	}
}