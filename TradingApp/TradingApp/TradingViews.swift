import SwiftUI

struct TradePresentation: Identifiable {
    let id = UUID()
    let symbol: String
    let side: OrderSide
}

struct MarketWatchView: View {
    @Environment(TradingStore.self) private var store
    @State private var trade: TradePresentation?

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack {
                        Label(store.isLiveAPI ? "Live API" : "Sandbox", systemImage: store.isLiveAPI ? "antenna.radiowaves.left.and.right" : "cpu")
                        Spacer()
                        if store.isBusy { ProgressView() }
                    }
                }
                Section("Watchlist") {
                    ForEach(store.quotes) { q in
                        QuoteRow(quote: q)
                            .contentShape(Rectangle())
                            .onTapGesture {
                                trade = TradePresentation(symbol: q.symbol, side: .buy)
                            }
                            .swipeActions(edge: .trailing) {
                                Button("Sell") {
                                    trade = TradePresentation(symbol: q.symbol, side: .sell)
                                }
                                .tint(.orange)
                                Button("Buy") {
                                    trade = TradePresentation(symbol: q.symbol, side: .buy)
                                }
                                .tint(.green)
                            }
                    }
                }
            }
            .navigationTitle("Markets")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await store.refreshAll() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(store.isBusy)
                }
            }
            .sheet(item: $trade) { route in
                TradeExecutionSheet(symbol: route.symbol, initialSide: route.side)
            }
        }
    }
}

private struct QuoteRow: View {
    let quote: Quote

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            VStack(alignment: .leading, spacing: 4) {
                Text(quote.symbol)
                    .font(.headline.monospaced())
                Text(quote.name)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 4) {
                Text(quote.price, format: .currency(code: "USD"))
                    .font(.headline.monospacedDigit())
                Text(quote.changePct, format: .percent.precision(.fractionLength(2)))
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(quote.changePct >= 0 ? Color.green : Color.red)
            }
        }
        .padding(.vertical, 4)
    }
}

struct PortfolioView: View {
    @Environment(TradingStore.self) private var store

    var body: some View {
        NavigationStack {
            List {
                if let err = store.lastError {
                    Section {
                        Text(err)
                            .foregroundStyle(.red)
                            .font(.footnote)
                    }
                }
                Section {
                    LabeledContent("Cash") {
                        Text(store.portfolio.cashBalance, format: .currency(code: "USD"))
                            .monospacedDigit()
                    }
                    LabeledContent("Equity") {
                        Text(totalEquity, format: .currency(code: "USD"))
                            .monospacedDigit()
                    }
                }
                Section("Holdings") {
                    if store.portfolio.holdings.isEmpty {
                        Text("No open positions")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(store.portfolio.holdings) { h in
                        HoldingRow(holding: h)
                    }
                }
                Section("Recent fills") {
                    ForEach(store.portfolio.recentExecutions) { e in
                        ExecutionRow(execution: e)
                    }
                }
            }
            .navigationTitle("Portfolio")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task { await store.refreshAll() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                    }
                    .disabled(store.isBusy)
                }
            }
        }
    }

    private var totalEquity: Decimal {
        store.portfolio.holdings.reduce(store.portfolio.cashBalance) { $0 + $1.marketValue }
    }
}

private struct HoldingRow: View {
    let holding: Holding

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(holding.symbol)
                    .font(.headline.monospaced())
                Spacer()
                Text(holding.marketValue, format: .currency(code: "USD"))
                    .font(.subheadline.monospacedDigit())
            }
            HStack {
                Text("\(holding.quantity, format: .number.precision(.fractionLength(0...4))) sh @ \(holding.averageCost, format: .currency(code: "USD"))")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(holding.unrealizedPL, format: .currency(code: "USD"))
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(holding.unrealizedPL >= 0 ? Color.green : Color.red)
            }
        }
        .padding(.vertical, 4)
    }
}

private struct ExecutionRow: View {
    let execution: Execution

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text(execution.side == .buy ? "Bought" : "Sold")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(execution.symbol)
                    .font(.headline.monospaced())
            }
            Spacer()
            VStack(alignment: .trailing, spacing: 2) {
                Text("\(execution.quantity, format: .number.precision(.fractionLength(0...4))) @ \(execution.price, format: .currency(code: "USD"))")
                    .font(.subheadline.monospacedDigit())
                Text(execution.executedAt, style: .time)
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
            }
        }
    }
}

struct TradeExecutionSheet: View {
    @Environment(TradingStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    let symbol: String
    let initialSide: OrderSide

    @State private var side: OrderSide
    @State private var quantityString: String = "1"
    @State private var didSubmit = false

    init(symbol: String, initialSide: OrderSide) {
        self.symbol = symbol
        self.initialSide = initialSide
        _side = State(initialValue: initialSide)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Order") {
                    Picker("Side", selection: $side) {
                        Text("Buy").tag(OrderSide.buy)
                        Text("Sell").tag(OrderSide.sell)
                    }
                    .pickerStyle(.segmented)
                    LabeledContent("Symbol") {
                        Text(symbol).font(.headline.monospaced())
                    }
                    TextField("Quantity", text: $quantityString)
                        .keyboardType(.decimalPad)
                        .font(.title2.monospacedDigit())
                }
                Section {
                    Button {
                        Task {
                            didSubmit = true
                            guard let qty = Decimal(string: quantityString.replacingOccurrences(of: ",", with: "")), qty > 0 else {
                                didSubmit = false
                                return
                            }
                            if await store.placeOrder(symbol: symbol, side: side, quantity: qty) != nil {
                                dismiss()
                            }
                            didSubmit = false
                        }
                    } label: {
                        HStack {
                            Spacer()
                            Text(side == .buy ? "Buy shares" : "Sell shares")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                    .disabled(store.isBusy || didSubmit)
                }
            }
            .navigationTitle("Trade")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }
}

struct ConnectionSettingsView: View {
    @Environment(TradingStore.self) private var store
    @State private var baseURL: String = CredentialStore.baseURLString() ?? ""
    @State private var token: String = ""
    @State private var pinHashes: String = UserDefaults.standard.string(forKey: "trading_spki_pins") ?? ""
    @State private var status: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("HTTPS only. Bearer token and base URL are stored in the Keychain. Optional SPKI SHA-256 (Base64) pins disable trust-on-first-use for pinned hosts.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
                Section("API endpoint") {
                    TextField("https://api.yourbroker.com", text: $baseURL)
                        .textContentType(.URL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                    SecureField("Bearer token", text: $token)
                    TextField("SPKI pins (comma-separated Base64)", text: $pinHashes, axis: .vertical)
                        .lineLimit(3 ... 6)
                }
                Section {
                    Button("Save & connect") {
                        save()
                    }
                    .disabled(store.isBusy)
                    Button("Use sandbox only", role: .destructive) {
                        try? CredentialStore.clearAll()
                        UserDefaults.standard.removeObject(forKey: "trading_spki_pins")
                        baseURL = ""
                        token = ""
                        pinHashes = ""
                        store.refreshCredentials()
                        Task { await store.refreshAll() }
                        status = "Cleared. Running in sandbox."
                    }
                }
                if let status {
                    Section {
                        Text(status)
                            .font(.footnote)
                    }
                }
            }
            .navigationTitle("Secure API")
            .onAppear {
                baseURL = CredentialStore.baseURLString() ?? ""
                token = CredentialStore.bearerToken() ?? ""
                pinHashes = UserDefaults.standard.string(forKey: "trading_spki_pins") ?? ""
            }
        }
    }

    private func save() {
        status = nil
        let trimmed = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.isEmpty == false, let url = URL(string: trimmed), url.scheme?.lowercased() == "https" else {
            status = "Base URL must be https://"
            return
        }
        do {
            UserDefaults.standard.set(pinHashes, forKey: "trading_spki_pins")
            try CredentialStore.saveBaseURL(trimmed)
            let tok = token.trimmingCharacters(in: .whitespacesAndNewlines)
            if tok.isEmpty == false {
                try CredentialStore.saveBearerToken(tok)
            }
            Task { @MainActor in
                store.refreshCredentials()
                status = "Saved."
                await store.refreshAll()
            }
        } catch {
            status = error.localizedDescription
        }
    }

}
