var wg sync.WaitGroup
	operations := []func() error{
		func() error { return bank.Deposit("alice_01", 2500) },
		func() error { return bank.Withdraw("alice_01", 1000) },
		func() error { return bank.Deposit("bob_01", 7500) },
		func() error { return bank.Withdraw("bob_01", 2000) },
		func() error {
			_, err := bank.GetBalance("alice_01")
			return err
		},
		func() error {
			_, err := bank.GetBalance("bob_01")
			return err
		},
	}