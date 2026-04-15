import SwiftUI

struct PortfolioView: View {
    @EnvironmentObject var session: TradingSession
    @EnvironmentObject var market: MarketRealtime

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Total value")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text(session.totalValue, format: .currency(code: "USD"))
                            .font(.title.bold().monospaced())
                        HStack {
                            Label("Cash", systemImage: "dollarsign.circle")
                            Spacer()
                            Text(session.cash, format: .currency(code: "USD"))
                                .monospaced()
                        }
                        .font(.subheadline)
                    }
                    .padding(.vertical, 4)
                }

                Section("Positions") {
                    if session.positions.isEmpty {
                        Text("No open positions")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(session.positions) { pos in
                            NavigationLink {
                                PositionDetailView(position: pos, market: market)
                            } label: {
                                PositionRow(position: pos, market: market)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Portfolio")
        }
    }
}

private struct PositionRow: View {
    let position: Position
    @ObservedObject var market: MarketRealtime

    var body: some View {
        let last = market.quote(for: position.symbol)?.last ?? position.averageCost
        let mkt = Decimal(position.quantity) * last
        let cost = Decimal(position.quantity) * position.averageCost
        let pnl = mkt - cost
        HStack {
            VStack(alignment: .leading) {
                Text(position.symbol)
                    .font(.headline.monospaced())
                Text("\(position.quantity) sh @ \(position.averageCost, format: .currency(code: "USD"))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing) {
                Text(mkt, format: .currency(code: "USD"))
                    .font(.headline.monospaced())
                Text(pnl, format: .currency(code: "USD"))
                    .font(.caption)
                    .foregroundStyle(pnl >= 0 ? Color.green : Color.red)
            }
        }
    }
}

private struct PositionDetailView: View {
    let position: Position
    @ObservedObject var market: MarketRealtime
    @EnvironmentObject var session: TradingSession
    @State private var showSell = false

    var body: some View {
        let q = market.quote(for: position.symbol)
        List {
            Section("Position") {
                LabeledContent("Symbol", value: position.symbol)
                LabeledContent("Quantity", value: "\(position.quantity)")
                LabeledContent("Avg cost", value: position.averageCost, format: .currency(code: "USD"))
                if let q {
                    LabeledContent("Last", value: q.last, format: .currency(code: "USD"))
                    LabeledContent("Bid / Ask") {
                        Text("\(q.bid, format: .currency(code: "USD")) / \(q.ask, format: .currency(code: "USD"))")
                    }
                }
            }
            Section {
                Button("Sell…") { showSell = true }
            }
        }
        .navigationTitle(position.symbol)
        .sheet(isPresented: $showSell) {
            if let quote = market.quote(for: position.symbol) {
                TradeSheet(quote: quote, market: market)
            } else {
                Text("Quote unavailable")
                    .padding()
            }
        }
    }
}
