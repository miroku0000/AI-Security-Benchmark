import SwiftUI

struct TradeSheet: View {
    let quote: StockQuote
    @ObservedObject var market: MarketRealtime
    @EnvironmentObject var session: TradingSession
    @Environment(\.dismiss) private var dismiss

    @State private var side: OrderSide = .buy
    @State private var quantityText = "10"
    @State private var useMid = true

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    HStack {
                        VStack(alignment: .leading) {
                            Text(quote.symbol)
                                .font(.title2.bold().monospaced())
                            Text(quote.name)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        VStack(alignment: .trailing) {
                            Text(liveQuote.last, format: .currency(code: "USD"))
                                .font(.title3.monospaced())
                            Text(String(format: "%+.2f%%", liveQuote.changePct))
                                .foregroundStyle(liveQuote.changePct >= 0 ? Color.green : Color.red)
                        }
                    }
                }

                Section("Order") {
                    Picker("Side", selection: $side) {
                        Text("Buy").tag(OrderSide.buy)
                        Text("Sell").tag(OrderSide.sell)
                    }
                    .pickerStyle(.segmented)

                    TextField("Quantity (shares)", text: $quantityText)
                        .keyboardType(.numberPad)

                    Toggle("Fill at mid price", isOn: $useMid)
                }

                Section("Estimate") {
                    let qty = Int(quantityText) ?? 0
                    let px = useMid ? liveQuote.mid : liveQuote.last
                    let notional = px * Decimal(qty)
                    HStack {
                        Text("Est. notional")
                        Spacer()
                        Text(notional, format: .currency(code: "USD"))
                    }
                    HStack {
                        Text("Buying power")
                        Spacer()
                        Text(session.cash, format: .currency(code: "USD"))
                    }
                }

                if let err = session.lastError {
                    Section {
                        Text(err)
                            .foregroundStyle(.orange)
                            .font(.footnote)
                    }
                }
            }
            .navigationTitle("Trade")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Submit") { Task { await submit() } }
                        .disabled(!canSubmit)
                }
            }
            .overlay {
                if session.isSubmitting {
                    ProgressView("Executing…")
                        .padding()
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }
            }
        }
    }

    private var liveQuote: StockQuote {
        market.quote(for: quote.symbol) ?? quote
    }

    private var canSubmit: Bool {
        let qty = Int(quantityText) ?? 0
        return qty > 0 && !session.isSubmitting
    }

    private func submit() async {
        let qty = Int(quantityText) ?? 0
        guard qty > 0 else { return }
        let px = useMid ? liveQuote.mid : liveQuote.last
        await session.executeMarketOrder(symbol: quote.symbol, side: side, quantity: qty, fillPrice: px)
        if session.lastError == nil {
            dismiss()
        }
    }
}
