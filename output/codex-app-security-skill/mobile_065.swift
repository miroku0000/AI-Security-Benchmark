LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
                ForEach(model.watchlist, id: \.self) { symbol in
                    let quote = model.quotes[symbol]
                    Button {
                        model.tradeSymbol = symbol
                    } label: {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(symbol)
                                .font(.headline)
                                .foregroundStyle(.primary)
                            Text(quote?.price.currencyString ?? "--")
                                .font(.title3.weight(.semibold))
                                .foregroundStyle(.primary)
                                .privacySensitive()
                            HStack {
                                Image(systemName: (quote?.change ?? 0) >= 0 ? "arrow.up.right" : "arrow.down.right")
                                Text((quote?.change ?? 0).signedCurrencyString)
                            }
                            .font(.footnote.weight(.medium))
                            .foregroundStyle((quote?.change ?? 0) >= 0 ? .green : .red)
                            Text(quote.map { DateFormatter.tradeTime.string(from: $0.updatedAt) } ?? "Waiting for quote")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, minHeight: 112, alignment: .leading)
                        .padding()
                        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 18, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }