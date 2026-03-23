for _, result := range results {
		switch result.Type {
		case BalanceCheck:
			if result.Err != nil {
				fmt.Printf("Balance check for %s failed: %v\n", result.Account, result.Err)
			} else {
				fmt.Printf("Balance for %s: %d\n", result.Account, result.Balance)
			}
		case DepositTx:
			if result.Err != nil {
				fmt.Printf("Deposit to %s failed: %v\n", result.Account, result.Err)
			} else {
				fmt.Printf("Deposit to %s succeeded, new balance: %d\n", result.Account, result.Balance)
			}
		case WithdrawTx:
			if result.Err != nil {
				fmt.Printf("Withdrawal from %s failed: %v\n", result.Account, result.Err)
			} else {
				fmt.Printf("Withdrawal from %s succeeded, new balance: %d\n", result.Account, result.Balance)
			}
		}
	}
}