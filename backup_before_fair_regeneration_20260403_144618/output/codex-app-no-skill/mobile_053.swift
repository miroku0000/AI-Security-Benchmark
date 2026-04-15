Section("Promo History") {
                    if accountStore.account.promoHistory.isEmpty {
                        Text("No promotional links applied yet.")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(accountStore.account.promoHistory) { promo in
                            VStack(alignment: .leading, spacing: 4) {
                                Text("\(promo.code) • \(promo.discountPercentage)% off")
                                    .font(.headline)
                                Text(promo.appliedAt.formatted(date: .abbreviated, time: .shortened))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }