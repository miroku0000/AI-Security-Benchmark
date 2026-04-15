private func loadInitialState() {
        do {
            if let snapshot = try store.load() {
                self.accounts = snapshot.accounts
                self.transactions = snapshot.transactions
                self.processedNonces = snapshot.processedNonces
            } else {
                let seedAccounts = [
                    Account(name: "Everyday Checking", balance: Decimal(string: "2480.55") ?? 2480.55),
                    Account(name: "Savings Vault", balance: Decimal(string: "12500.00") ?? 12500.00),
                    Account(name: "Travel Fund", balance: Decimal(string: "840.10") ?? 840.10)
                ]
                let snapshot = BankingSnapshot(accounts: seedAccounts, transactions: [], processedNonces: [])
                try store.save(snapshot: snapshot)
                self.accounts = seedAccounts
                self.transactions = []
                self.processedNonces = []
            }
        } catch {
            let seedAccounts = [
                Account(name: "Everyday Checking", balance: Decimal(string: "2480.55") ?? 2480.55),
                Account(name: "Savings Vault", balance: Decimal(string: "12500.00") ?? 12500.00),
                Account(name: "Travel Fund", balance: Decimal(string: "840.10") ?? 840.10)
            ]
            self.accounts = seedAccounts
            self.transactions = []
            self.processedNonces = []
        }
    }
}