import SwiftUI

struct TradeSheet: View {
    @Environment(TradingEngine.self) private var engine
    @Environment(\.dismiss) private var dismiss

    let symbol: String
    @State private var side: OrderSide = .buy
    @State private var qtyText = "10"
    @State private var limitText = ""
    @State private var useLimit = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Side", selection: $side) {
                        Text("Buy").tag(OrderSide.buy)
                        Text("Sell").tag(OrderSide.sell)
                    }
                    .pickerStyle(.segmented)
                    TextField("Shares", text: $qtyText)
                        .keyboardType(.decimalPad)
                    Toggle("Limit order", isOn: $useLimit)
                    if useLimit {
                        TextField("Limit price", text: $limitText)
                            .keyboardType(.decimalPad)
                    }
                } header: {
                    Text(symbol)
                }
                if let px = engine.instruments.first(where: { $0.symbol == symbol }) {
                    Section("Quote") {
                        LabeledContent("Last", value: formatMoney(px.last))
                        LabeledContent("Bid / Ask", value: "\(formatMoney(px.bid)) / \(formatMoney(px.ask))")
                    }
                }
                if let err = engine.lastError {
                    Section {
                        Text(err).foregroundStyle(.red)
                    }
                }
            }
            .navigationTitle("Trade")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Submit") { Task { await submit() } }
                        .disabled(engine.isSubmitting || parseQty() == nil)
                }
            }
        }
    }

    private func parseQty() -> Decimal? {
        Decimal(string: qtyText.replacingOccurrences(of: ",", with: "."))
    }

    private func parseLimit() -> Decimal? {
        guard useLimit else { return nil }
        return Decimal(string: limitText.replacingOccurrences(of: ",", with: "."))
    }

    private func submit() async {
        guard let q = parseQty() else { return }
        let lim = parseLimit()
        await engine.execute(symbol: symbol, side: side, quantity: q, limit: lim)
        if engine.lastError == nil {
            dismiss()
        }
    }

    private func formatMoney(_ d: Decimal) -> String {
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        return f.string(from: d as NSDecimalNumber) ?? "$0.00"
    }
}
