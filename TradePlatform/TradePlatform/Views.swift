import SwiftUI

struct RootTabView: View {
    @EnvironmentObject private var portfolio: PortfolioStore
    @EnvironmentObject private var quotes: QuoteStreamService

    var body: some View {
        TabView {
            PortfolioView()
                .tabItem { Label("Portfolio", systemImage: "chart.pie.fill") }
            MarketsView()
                .tabItem { Label("Markets", systemImage: "waveform.path.ecg") }
            TradeView()
                .tabItem { Label("Trade", systemImage: "arrow.left.arrow.right.circle.fill") }
            SettingsView()
                .tabItem { Label("Account", systemImage: "lock.shield.fill") }
        }
        .tint(Color(red: 0.2, green: 0.78, blue: 0.55))
        .onAppear {
            quotes.connectLive(url: nil)
        }
        .onChange(of: quotes.quotes) { _, new in
            portfolio.syncPrices(from: new)
        }
    }
}

struct PortfolioView: View {
    @EnvironmentObject private var portfolio: PortfolioStore

    var body: some View {
        NavigationStack {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Total equity")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(portfolio.snapshot.equity, format: .currency(code: "USD"))
                            .font(.system(size: 34, weight: .bold, design: .rounded))
                        HStack {
                            Text(portfolio.snapshot.cashBalance, format: .currency(code: "USD"))
                                .font(.footnote)
                            Spacer()
                            Text("Cash")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .padding(.vertical, 6)
                }
                Section("Holdings") {
                    if portfolio.snapshot.positions.isEmpty {
                        Text("No open positions")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(portfolio.snapshot.positions) { p in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(p.symbol)
                                        .font(.headline)
                                    Spacer()
                                    Text(p.marketValue, format: .currency(code: "USD"))
                                        .font(.headline)
                                }
                                HStack {
                                    Text("\(p.quantity) sh @ \(p.averageCost, format: .currency(code: "USD"))")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                    Spacer()
                                    Text(p.unrealizedPL, format: .currency(code: "USD"))
                                        .font(.caption)
                                        .foregroundStyle(p.unrealizedPL >= 0 ? Color.green : Color.red)
                                }
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
                Section("Recent orders") {
                    if portfolio.snapshot.orders.isEmpty {
                        Text("No orders yet")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(portfolio.snapshot.orders.prefix(12)) { o in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text("\(o.side.rawValue.uppercased()) \(o.symbol)")
                                        .font(.subheadline.weight(.semibold))
                                    Text(o.submittedAt.formatted(date: .abbreviated, time: .shortened))
                                        .font(.caption2)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Text(o.status.rawValue.capitalized)
                                    .font(.caption.weight(.medium))
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Capsule().fill(Color.secondary.opacity(0.2)))
                            }
                        }
                    }
                }
            }
            .navigationTitle("Portfolio")
        }
    }
}

struct MarketsView: View {
    @EnvironmentObject private var quotes: QuoteStreamService

    var body: some View {
        NavigationStack {
            List(quotes.quotes.values.sorted(by: { $0.symbol < $1.symbol })) { q in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(q.symbol)
                            .font(.headline)
                        Spacer()
                        Text(q.last, format: .currency(code: "USD"))
                            .font(.headline.monospacedDigit())
                    }
                    Text(q.name)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    HStack {
                        Text("Bid \(q.bid, format: .currency(code: "USD"))")
                        Spacer()
                        Text("Ask \(q.ask, format: .currency(code: "USD"))")
                    }
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.secondary)
                    HStack {
                        Text(NSDecimalNumber(decimal: q.changePct).doubleValue / 100.0, format: .percent.precision(.fractionLength(2)))
                            .foregroundStyle(q.changePct >= 0 ? Color.green : Color.red)
                        Spacer()
                        Text(q.timestamp.formatted(date: .omitted, time: .standard))
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }
                }
                .padding(.vertical, 4)
            }
            .navigationTitle("Live quotes")
            .overlay {
                if quotes.quotes.isEmpty {
                    ContentUnavailableView("Connecting", systemImage: "antenna.radiowaves.left.and.right", description: Text("Streaming mock market data"))
                }
            }
        }
    }
}

struct TradeView: View {
    @EnvironmentObject private var portfolio: PortfolioStore
    @EnvironmentObject private var quotes: QuoteStreamService
    @State private var symbol = "AAPL"
    @State private var quantityText = "10"
    @State private var side: OrderSide = .buy
    @State private var useLimit = false
    @State private var limitText = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Order") {
                    Picker("Side", selection: $side) {
                        Text("Buy").tag(OrderSide.buy)
                        Text("Sell").tag(OrderSide.sell)
                    }
                    .pickerStyle(.segmented)
                    TextField("Symbol", text: $symbol)
                        .textInputAutocapitalization(.characters)
                    TextField("Quantity", text: $quantityText)
                        .keyboardType(.numberPad)
                    Toggle("Limit price", isOn: $useLimit)
                    if useLimit {
                        TextField("Limit", text: $limitText)
                            .keyboardType(.decimalPad)
                    }
                }
                Section("Reference") {
                    if let q = quotes.quotes[symbol.uppercased()] {
                        LabeledContent("Last") { Text(q.last, format: .currency(code: "USD")) }
                        LabeledContent("Spread") {
                            Text("\(q.bid, format: .currency(code: "USD")) – \(q.ask, format: .currency(code: "USD"))")
                        }
                    } else {
                        Text("Enter a symbol on Markets tab or use a default price.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
                Section {
                    Button {
                        Task {
                            let qty = Int(quantityText) ?? 0
                            let lim: Decimal? = useLimit ? Decimal(string: limitText.replacingOccurrences(of: ",", with: "")) : nil
                            let ref = quotes.quotes[symbol.uppercased()]?.last
                            await portfolio.executeTrade(symbol: symbol, side: side, quantity: qty, limitPrice: lim, referencePrice: ref)
                        }
                    } label: {
                        HStack {
                            Spacer()
                            if portfolio.isPlacingOrder {
                                ProgressView()
                            } else {
                                Text(side == .buy ? "Buy" : "Sell")
                                    .fontWeight(.semibold)
                            }
                            Spacer()
                        }
                    }
                    .disabled(portfolio.isPlacingOrder)
                }
                if let msg = portfolio.lastTradeMessage {
                    Section {
                        Text(msg)
                            .font(.footnote)
                    }
                }
            }
            .navigationTitle("Trade")
        }
    }
}

struct SettingsView: View {
    @EnvironmentObject private var portfolio: PortfolioStore

    var body: some View {
        NavigationStack {
            Form {
                Section("Secure API") {
                    Toggle("Route orders to live API", isOn: $portfolio.useLiveAPI)
                    SecureField("Bearer token", text: $portfolio.demoToken)
                        .textContentType(.password)
                    Button("Store token in Keychain") {
                        portfolio.applyDemoAuth()
                    }
                    Text("HTTPS-only session, TLS 1.2+, optional certificate pinning via SecureURLSessionFactory.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section {
                    Button("Refresh portfolio (live API)") {
                        Task { await portfolio.refreshFromAPI() }
                    }
                    .disabled(!portfolio.useLiveAPI)
                }
            }
            .navigationTitle("Account")
        }
    }
}
