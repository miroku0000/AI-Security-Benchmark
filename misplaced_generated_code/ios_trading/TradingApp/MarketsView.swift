import SwiftUI

struct MarketsView: View {
    @EnvironmentObject var market: MarketRealtime
    @EnvironmentObject var session: TradingSession
    @State private var selected: StockQuote?
    @State private var search = ""

    private var filtered: [StockQuote] {
        let q = search.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
        if q.isEmpty { return market.quotes }
        return market.quotes.filter { $0.symbol.contains(q) || $0.name.localizedCaseInsensitiveContains(search) }
    }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    ForEach(filtered) { quote in
                        Button {
                            selected = quote
                        } label: {
                            QuoteRow(quote: quote)
                        }
                        .buttonStyle(.plain)
                    }
                } header: {
                    HStack {
                        Text("Symbol")
                        Spacer()
                        Text("Last")
                        Text("Chg%")
                            .frame(width: 64, alignment: .trailing)
                    }
                    .font(.caption)
                    .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Markets")
            .searchable(text: $search, prompt: "Search symbols")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    CashBadge(cash: session.cash)
                }
            }
            .sheet(item: $selected) { quote in
                TradeSheet(quote: quote, market: market)
            }
        }
    }
}

private struct QuoteRow: View {
    let quote: StockQuote

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 2) {
                Text(quote.symbol)
                    .font(.headline.monospaced())
                Text(quote.name)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text(formatMoney(quote.last))
                    .font(.headline.monospaced())
                Text("Bid \(formatMoney(quote.bid))  Ask \(formatMoney(quote.ask))")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
            Text(String(format: "%+.2f%%", quote.changePct))
                .font(.subheadline.monospaced())
                .foregroundStyle(quote.changePct >= 0 ? Color.green : Color.red)
                .frame(width: 72, alignment: .trailing)
        }
        .padding(.vertical, 4)
    }

    private func formatMoney(_ d: Decimal) -> String {
        let n = NSDecimalNumber(decimal: d)
        let f = NumberFormatter()
        f.numberStyle = .currency
        f.currencyCode = "USD"
        f.maximumFractionDigits = 2
        return f.string(from: n) ?? "\(d)"
    }
}

private struct CashBadge: View {
    let cash: Decimal

    var body: some View {
        Text({
            let n = NSDecimalNumber(decimal: cash)
            let f = NumberFormatter()
            f.numberStyle = .currency
            f.currencyCode = "USD"
            f.maximumFractionDigits = 0
            return f.string(from: n) ?? ""
        }())
        .font(.caption.monospaced())
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial, in: Capsule())
    }
}
