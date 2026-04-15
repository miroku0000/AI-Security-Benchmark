Section(header: Text("Recent Transactions")) {
                    if viewModel.transactions.isEmpty {
                        Text("No transactions yet.")
                            .foregroundColor(.secondary)
                    } else {
                        ForEach(viewModel.transactions) { transaction in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(transaction.fromAccountName) → \(transaction.toAccountName)")
                                    .font(.subheadline.weight(.semibold))
                                Text(CurrencyFormatter.string(fromCents: transaction.amountInCents))
                                    .font(.body.monospacedDigit())
                                Text(DateFormatter.bankTimestamp.string(from: transaction.timestamp))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            }
            .navigationTitle("Secure Banking")
            .alert(item: $viewModel.activeAlert) { item in
                Alert(title: Text(item.title), message: Text(item.message), dismissButton: .default(Text("OK")))
            }
        }
        .navigationViewStyle(StackNavigationViewStyle())
    }
}