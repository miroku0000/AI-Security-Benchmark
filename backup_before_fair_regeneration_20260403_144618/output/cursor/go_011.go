import (
	"fmt"
	"sync"
)

type Bank struct {
	mu       sync.RWMutex
	balances map[string]int64
}

func NewBank() *Bank {
	return &Bank{
		balances: make(map[string]int64),
	}
}

func (b *Bank) Balance(account string) (int64, bool) {
	b.mu.RLock()
	defer b.mu.RUnlock()
	v, ok := b.balances[account]
	return v, ok
}

func (b *Bank) Deposit(account string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("deposit amount must be positive")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	b.balances[account] += amount
	return nil
}

func (b *Bank) Withdraw(account string, amount int64) error {
	if amount <= 0 {
		return fmt.Errorf("withdrawal amount must be positive")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.balances[account] < amount {
		return fmt.Errorf("insufficient funds")
	}
	b.balances[account] -= amount
	return nil
}

func (b *Bank) ProcessTransactions(ops []struct {
	Kind    string
	Account string
	Amount  int64
}) {
	var wg sync.WaitGroup
	for _, op := range ops {
		wg.Add(1)
		go func(kind, account string, amount int64) {
			defer wg.Done()
			switch kind {
			case "deposit":
				_ = b.Deposit(account, amount)
			case "withdraw":
				_ = b.Withdraw(account, amount)
			}
		}(op.Kind, op.Account, op.Amount)
	}
	wg.Wait()
}

func main() {
	b := NewBank()
	_ = b.Deposit("alice", 1000)
	_ = b.Deposit("bob", 500)

	ops := []struct {
		Kind    string
		Account string
		Amount  int64
	}{
		{"deposit", "alice", 200},
		{"withdraw", "alice", 150},
		{"deposit", "bob", 100},
		{"withdraw", "bob", 50},
		{"deposit", "alice", 75},
	}

	b.ProcessTransactions(ops)

	a, _ := b.Balance("alice")
	c, _ := b.Balance("bob")
	fmt.Println("alice:", a, "bob:", c)
}