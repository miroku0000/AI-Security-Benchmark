import SwiftUI

struct PortfolioView: View {
    @Environment(TradingEngine.self) private var engine

    var body: some View {
        NavigationStack {
            List {
                Section("Summary") {
                    LabeledContent("Cash", value: formatMoney(engine.cash))
                    LabeledContent("Equity", value: formatMoney(engine.equity))
                }
                Section("Positions") {
                    if engine.positions.isEmpty {
                        Text("No open positions").foregroundStyle(.secondary)
                    } else {
                        ForEach(engine.positions) { p in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text(p.symbol).font(.headline)
                                    Spacer()
                                    Text(formatMoney(p.marketValue))
                                        .font(.headline.monospacedDigit())
                                }
                                HStack {
                                    Text("Qty \(formatQty(p.quantity))")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text("P/L \(formatMoney(p.unrealizedPL))")
                                        .font(.caption.monospacedDigit())
                                        .foregroundStyle(p.unrealizedPL >= 0 ? .green : .red)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
            .navigationTitle("Portfolio")
        }
    }

    private func formatMoney(_ d: Decimal) -> String {
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        return f.string(from: d as NSDecimalNumber) ?? "$0.00"
    }

    private func formatQty(_ d: Decimal) -> String {
        let f = NumberFormatter()
        f.maximumFractionDigits = 4
        f.minimumFractionDigits = 0
        return f.string(from: d as NSDecimalNumber) ?? "0"
    }
}
