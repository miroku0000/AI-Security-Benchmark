import SwiftUI

private struct SymbolRoute: Identifiable, Hashable {
    let id: String
}

struct MarketsView: View {
    @Environment(TradingEngine.self) private var engine
    @State private var tradeRoute: SymbolRoute?

    var body: some View {
        NavigationStack {
            List(engine.instruments) { i in
                Button {
                    tradeRoute = SymbolRoute(id: i.symbol)
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(i.symbol)
                                .font(.headline)
                                .foregroundStyle(.primary)
                            Text(i.name)
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        VStack(alignment: .trailing, spacing: 4) {
                            Text(formatMoney(i.last))
                                .font(.headline.monospacedDigit())
                            Text(formatPct(i.changePct))
                                .font(.caption.monospacedDigit())
                                .foregroundStyle(i.changePct >= 0 ? .green : .red)
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
            .navigationTitle("Markets")
            .sheet(item: $tradeRoute) { r in
                TradeSheet(symbol: r.id)
            }
        }
    }

    private func formatMoney(_ d: Decimal) -> String {
        let n = NSDecimalNumber(decimal: d)
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        return f.string(from: n) ?? "$0.00"
    }

    private func formatPct(_ d: Decimal) -> String {
        let v = (d as NSDecimalNumber).doubleValue
        return String(format: "%+.2f%%", v)
    }
}
