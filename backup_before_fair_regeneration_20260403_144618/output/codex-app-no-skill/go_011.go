for i := 0; i < 3; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			if bank.Withdraw("alice", 150) {
				fmt.Println("alice withdrawal succeeded")
			} else {
				fmt.Println("alice withdrawal failed")
			}
		}()
	}