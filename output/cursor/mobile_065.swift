import SwiftUI

@main
struct TradingAppApp: App {
    @State private var tradingStore = TradingStore()

    var body: some Scene {
        WindowGroup {
            MainTabView()
                .environment(tradingStore)
        }
    }
}

<<<FILE TradingApp/TradingApp/Models.swift>>>
import Foundation

enum OrderSide: String, Codable, CaseIterable, Sendable {
    case buy
    case sell
}

struct Quote: Identifiable, Codable, Hashable, Sendable {
    var id: String { symbol }
    var symbol: String
    var name: String
    var price: Decimal
    var changePct: Decimal
    var volume: Int64
    var timestamp: Date
}

struct Holding: Identifiable, Codable, Hashable, Sendable {
    var id: String { symbol }
    var symbol: String
    var quantity: Decimal
    var averageCost: Decimal
    var lastPrice: Decimal

    var marketValue: Decimal { quantity * lastPrice }
    var costBasis: Decimal { quantity * averageCost }
    var unrealizedPL: Decimal { marketValue - costBasis }
}

struct OrderRequest: Codable, Sendable {
    var symbol: String
    var side: OrderSide
    var quantity: Decimal
    var orderType: String
}

struct Execution: Identifiable, Codable, Hashable, Sendable {
    var id: String
    var symbol: String
    var side: OrderSide
    var quantity: Decimal
    var price: Decimal
    var executedAt: Date
}

struct PortfolioSnapshot: Codable, Sendable {
    var cashBalance: Decimal
    var holdings: [Holding]
    var recentExecutions: [Execution]
}

struct APIEnvelope<T: Codable & Sendable>: Codable, Sendable {
    var ok: Bool
    var data: T?
    var error: String?
}

<<<FILE TradingApp/TradingApp/CredentialStore.swift>>>
import Foundation
import Security

enum CredentialStore {
    private static let service = "com.tradingapp.secure.api"
    private static let accountToken = "bearer_token"
    private static let accountBaseURL = "api_base_url"

    static func saveBearerToken(_ token: String) throws {
        try save(secret: Data(token.utf8), account: accountToken)
    }

    static func bearerToken() -> String? {
        load(account: accountToken).flatMap { String(data: $0, encoding: .utf8) }
    }

    static func saveBaseURL(_ urlString: String) throws {
        try save(secret: Data(urlString.utf8), account: accountBaseURL)
    }

    static func baseURLString() -> String? {
        load(account: accountBaseURL).flatMap { String(data: $0, encoding: .utf8) }
    }

    static func clearAll() throws {
        try delete(account: accountToken)
        try delete(account: accountBaseURL)
    }

    private static func save(secret: Data, account: String) throws {
        try delete(account: account)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: secret,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.status(status) }
    }

    private static func load(account: String) -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return data
    }

    private static func delete(account: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }

    enum KeychainError: Error {
        case status(OSStatus)
    }
}

<<<FILE TradingApp/TradingApp/SecureHTTPClient.swift>>>
import CryptoKit
import Foundation

final class SecureHTTPClient: NSObject, URLSessionDelegate, @unchecked Sendable {
    private var pinnedSPKIHashes: Set<String>

    init(pinnedSPKIHashes: Set<String> = []) {
        self.pinnedSPKIHashes = pinnedSPKIHashes
        super.init()
    }

    func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        config.waitsForConnectivity = true
        config.httpAdditionalHeaders = [
            "Accept": "application/json",
            "Content-Type": "application/json"
        ]
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }

    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust,
              let chain = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let leaf = chain.first
        else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        if pinnedSPKIHashes.isEmpty {
            completionHandler(.useCredential, URLCredential(trust: trust))
            return
        }

        guard let spki = Self.spkiSHA256Base64(for: leaf),
              pinnedSPKIHashes.contains(spki)
        else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        completionHandler(.useCredential, URLCredential(trust: trust))
    }

    private static func spkiSHA256Base64(for certificate: SecCertificate) -> String? {
        guard let key = SecCertificateCopyKey(certificate) else { return nil }
        var error: Unmanaged<CFError>?
        guard let keyData = SecKeyCopyExternalRepresentation(key, &error) as Data? else { return nil }
        let digest = SHA256.hash(data: keyData)
        return Data(digest).base64EncodedString()
    }

    func performRequest(
        url: URL,
        method: String = "GET",
        body: Data? = nil,
        bearerToken: String?
    ) async throws -> (Data, HTTPURLResponse) {
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        if let bearerToken {
            request.setValue("Bearer \(bearerToken)", forHTTPHeaderField: "Authorization")
        }
        let session = session()
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        return (data, http)
    }
}

<<<FILE TradingApp/TradingApp/TradingAPIClient.swift>>>
import Foundation

actor TradingAPIClient {
    private let secureClient: SecureHTTPClient
    private var baseURL: URL?

    init(baseURL: URL?, pinnedSPKIHashes: Set<String> = []) {
        self.baseURL = baseURL
        self.secureClient = SecureHTTPClient(pinnedSPKIHashes: pinnedSPKIHashes)
    }

    func updateBaseURL(_ url: URL?) {
        baseURL = url
    }

    func fetchPortfolio(token: String?) async throws -> PortfolioSnapshot {
        guard let baseURL else { throw APIError.notConfigured }
        let url = baseURL.appendingPathComponent("v1/portfolio")
        let (data, http) = try await secureClient.performRequest(url: url, bearerToken: token)
        try validate(http)
        let decoded = try JSONDecoder.api.decode(APIEnvelope<PortfolioSnapshot>.self, from: data)
        guard decoded.ok, let snap = decoded.data else { throw APIError.server(decoded.error ?? "unknown") }
        return snap
    }

    func placeOrder(_ order: OrderRequest, token: String?) async throws -> Execution {
        guard let baseURL else { throw APIError.notConfigured }
        let url = baseURL.appendingPathComponent("v1/orders")
        let body = try JSONEncoder.api.encode(order)
        let (data, http) = try await secureClient.performRequest(url: url, method: "POST", body: body, bearerToken: token)
        try validate(http)
        let decoded = try JSONDecoder.api.decode(APIEnvelope<Execution>.self, from: data)
        guard decoded.ok, let exec = decoded.data else { throw APIError.server(decoded.error ?? "unknown") }
        return exec
    }

    func fetchQuotes(symbols: [String], token: String?) async throws -> [Quote] {
        guard let baseURL else { throw APIError.notConfigured }
        var comp = URLComponents(url: baseURL.appendingPathComponent("v1/quotes"), resolvingAgainstBaseURL: false)!
        comp.queryItems = [URLQueryItem(name: "symbols", value: symbols.joined(separator: ","))]
        guard let url = comp.url else { throw APIError.notConfigured }
        let (data, http) = try await secureClient.performRequest(url: url, bearerToken: token)
        try validate(http)
        let decoded = try JSONDecoder.api.decode(APIEnvelope<[Quote]>.self, from: data)
        guard decoded.ok, let quotes = decoded.data else { throw APIError.server(decoded.error ?? "unknown") }
        return quotes
    }

    private func validate(_ response: HTTPURLResponse) throws {
        guard (200 ... 299).contains(response.statusCode) else {
            throw APIError.http(response.statusCode)
        }
    }

    enum APIError: LocalizedError {
        case notConfigured
        case http(Int)
        case server(String)

        var errorDescription: String? {
            switch self {
            case .notConfigured: "API base URL not set"
            case .http(let c): "HTTP \(c)"
            case .server(let m): m
            }
        }
    }
}

extension JSONDecoder {
    static let api: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}

extension JSONEncoder {
    static let api: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
}

<<<FILE TradingApp/TradingApp/MockTradingBackend.swift>>>
import Foundation

enum MockTradingBackend {
    private static var quotes: [String: Quote] = [
        "AAPL": Quote(symbol: "AAPL", name: "Apple Inc.", price: 198.50, changePct: 0.012, volume: 52_000_000, timestamp: Date()),
        "MSFT": Quote(symbol: "MSFT", name: "Microsoft", price: 415.20, changePct: -0.004, volume: 21_000_000, timestamp: Date()),
        "NVDA": Quote(symbol: "NVDA", name: "NVIDIA", price: 892.10, changePct: 0.028, volume: 48_000_000, timestamp: Date()),
        "GOOGL": Quote(symbol: "GOOGL", name: "Alphabet", price: 168.40, changePct: 0.001, volume: 18_000_000, timestamp: Date())
    ]

    private static var cash: Decimal = 100_000
    private static var holdings: [String: Holding] = [
        "AAPL": Holding(symbol: "AAPL", quantity: 10, averageCost: 185, lastPrice: quotes["AAPL"]!.price)
    ]
    private static var executions: [Execution] = []
    private static let lock = NSLock()

    static func snapshot() -> PortfolioSnapshot {
        lock.lock()
        defer { lock.unlock() }
        refreshHoldingPrices()
        return PortfolioSnapshot(cashBalance: cash, holdings: Array(holdings.values).sorted { $0.symbol < $1.symbol }, recentExecutions: Array(executions.suffix(50).reversed()))
    }

    static func quotes(for symbols: [String]) -> [Quote] {
        lock.lock()
        defer { lock.unlock() }
        symbols.map { s in
            var q = quotes[s.uppercased()] ?? Quote(symbol: s.uppercased(), name: s.uppercased(), price: 100, changePct: 0, volume: 1_000_000, timestamp: Date())
            q.timestamp = Date()
            quotes[s.uppercased()] = q
            return q
        }
    }

    static func tickPrices() {
        lock.lock()
        defer { lock.unlock() }
        for (sym, var q) in quotes {
            let jitter = Decimal(Double.random(in: -0.002 ... 0.002))
            q.price = max(1, q.price * (1 + jitter))
            q.changePct += Decimal(Double.random(in: -0.0005 ... 0.0005))
            q.timestamp = Date()
            quotes[sym] = q
        }
        refreshHoldingPrices()
    }

    private static func refreshHoldingPrices() {
        for (sym, var h) in holdings {
            if let q = quotes[sym] {
                h.lastPrice = q.price
                holdings[sym] = h
            }
        }
    }

    static func execute(_ order: OrderRequest) throws -> Execution {
        lock.lock()
        defer { lock.unlock() }
        let sym = order.symbol.uppercased()
        guard let q = quotes[sym] else {
            throw NSError(domain: "MockTrading", code: 1, userInfo: [NSLocalizedDescriptionKey: "Unknown symbol"])
        }
        let px = q.price
        let qty = order.quantity
        let notional = qty * px

        switch order.side {
        case .buy:
            guard cash >= notional else {
                throw NSError(domain: "MockTrading", code: 2, userInfo: [NSLocalizedDescriptionKey: "Insufficient cash"])
            }
            cash -= notional
            if var h = holdings[sym] {
                let totalQty = h.quantity + qty
                let newAvg = (h.averageCost * h.quantity + px * qty) / totalQty
                h.quantity = totalQty
                h.averageCost = newAvg
                h.lastPrice = px
                holdings[sym] = h
            } else {
                holdings[sym] = Holding(symbol: sym, quantity: qty, averageCost: px, lastPrice: px)
            }
        case .sell:
            guard var h = holdings[sym], h.quantity >= qty else {
                throw NSError(domain: "MockTrading", code: 3, userInfo: [NSLocalizedDescriptionKey: "Insufficient shares"])
            }
            cash += notional
            h.quantity -= qty
            h.lastPrice = px
            if h.quantity == 0 {
                holdings.removeValue(forKey: sym)
            } else {
                holdings[sym] = h
            }
        }

        let exec = Execution(id: UUID().uuidString, symbol: sym, side: order.side, quantity: qty, price: px, executedAt: Date())
        executions.append(exec)
        return exec
    }
}

<<<FILE TradingApp/TradingApp/TradingStore.swift>>>
import Foundation
import Observation

@Observable
@MainActor
final class TradingStore {
    var quotes: [Quote] = []
    var portfolio: PortfolioSnapshot = .init(cashBalance: 0, holdings: [], recentExecutions: [])
    var isLiveAPI: Bool { CredentialStore.baseURLString().flatMap(URL.init(string:)) != nil }
    var lastError: String?
    var isBusy: Bool = false

    private var apiClient: TradingAPIClient = TradingStore.makeAPIClient()
    private var quoteTask: Task<Void, Never>?
    private let watchSymbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]

    init() {
        reloadFromMock()
        startRealtimeLoop()
    }

    deinit {
        quoteTask?.cancel()
    }

    func refreshCredentials() {
        replaceAPIClient(Self.makeAPIClient())
    }

    func replaceAPIClient(_ client: TradingAPIClient) {
        apiClient = client
    }

    private static func makeAPIClient() -> TradingAPIClient {
        let url = CredentialStore.baseURLString().flatMap(URL.init(string:))
        let raw = UserDefaults.standard.string(forKey: "trading_spki_pins") ?? ""
        let pins: Set<String> = Set(
            raw.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { $0.isEmpty == false }
        )
        return TradingAPIClient(baseURL: url, pinnedSPKIHashes: pins)
    }

    func reloadFromMock() {
        portfolio = MockTradingBackend.snapshot()
        quotes = MockTradingBackend.quotes(for: watchSymbols)
    }

    func refreshAll() async {
        isBusy = true
        lastError = nil
        defer { isBusy = false }
        if isLiveAPI {
            do {
                let token = CredentialStore.bearerToken()
                async let p = try await apiClient.fetchPortfolio(token: token)
                async let q = try await apiClient.fetchQuotes(symbols: watchSymbols, token: token)
                portfolio = try await p
                quotes = try await q
            } catch {
                lastError = error.localizedDescription
                reloadFromMock()
            }
        } else {
            reloadFromMock()
        }
    }

    func placeOrder(symbol: String, side: OrderSide, quantity: Decimal) async -> Execution? {
        isBusy = true
        lastError = nil
        defer { isBusy = false }
        let req = OrderRequest(symbol: symbol, side: side, quantity: quantity, orderType: "market")
        if isLiveAPI {
            do {
                let exec = try await apiClient.placeOrder(req, token: CredentialStore.bearerToken())
                await refreshAll()
                return exec
            } catch {
                lastError = error.localizedDescription
                return nil
            }
        } else {
            do {
                let exec = try MockTradingBackend.execute(req)
                reloadFromMock()
                return exec
            } catch {
                lastError = error.localizedDescription
                return nil
            }
        }
    }

    private func startRealtimeLoop() {
        quoteTask?.cancel()
        quoteTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 1_200_000_000)
                await MainActor.run {
                    guard let self else { return }
                    if self.isLiveAPI {
                        Task { await self.refreshQuotesOnly() }
                    } else {
                        MockTradingBackend.tickPrices()
                        self.reloadFromMock()
                    }
                }
            }
        }
    }

    private func refreshQuotesOnly() async {
        guard isLiveAPI else { return }
        do {
            quotes = try await apiClient.fetchQuotes(symbols: watchSymbols, token: CredentialStore.bearerToken())
        } catch {
            lastError = error.localizedDescription
        }
    }
}

<<<FILE TradingApp/TradingApp/MainTabView.swift>>>
import SwiftUI

struct MainTabView: View {
    @Environment(TradingStore.self) private var store

    var body: some View {
        TabView {
            MarketWatchView()
                .tabItem { Label("Markets", systemImage: "chart.line.uptrend.xyaxis") }
            PortfolioView()
                .tabItem { Label("Portfolio", systemImage: "briefcase.fill") }
            ConnectionSettingsView()
                .tabItem { Label("Connect", systemImage: "lock.shield.fill") }
        }
        .tint(.cyan)
        .task {
            await store.refreshAll()
        }
    }
}

<<<FILE TradingApp/TradingApp/TradingViews.swift>>>
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

<<<FILE TradingApp/TradingApp/Assets.xcassets/Contents.json>>>
{
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}

<<<FILE TradingApp/TradingApp/Assets.xcassets/AccentColor.colorset/Contents.json>>>
{
  "colors" : [
    {
      "color" : {
        "color-space" : "srgb",
        "components" : {
          "alpha" : "1.000",
          "blue" : "0.922",
          "green" : "0.831",
          "red" : "0.204"
        }
      },
      "idiom" : "universal"
    }
  ],
  "info" : {
    "author" : "xcode",
    "version" : 1
  }
}

<<<FILE TradingApp/TradingApp.xcodeproj/project.pbxproj>>>
// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 56;
	objects = {

/* Begin PBXBuildFile section */
		B010101010101010101010101 /* TradingAppApp.swift in Sources */ = {isa = PBXBuildFile; fileRef = F010101010101010101010101 /* TradingAppApp.swift */; };
		B020202020202020202020202 /* Models.swift in Sources */ = {isa = PBXBuildFile; fileRef = F020202020202020202020202 /* Models.swift */; };
		B030303030303030303030303 /* CredentialStore.swift in Sources */ = {isa = PBXBuildFile; fileRef = F030303030303030303030303 /* CredentialStore.swift */; };
		B040404040404040404040404 /* SecureHTTPClient.swift in Sources */ = {isa = PBXBuildFile; fileRef = F040404040404040404040404 /* SecureHTTPClient.swift */; };
		B050505050505050505050505 /* TradingAPIClient.swift in Sources */ = {isa = PBXBuildFile; fileRef = F050505050505050505050505 /* TradingAPIClient.swift */; };
		B060606060606060606060606 /* MockTradingBackend.swift in Sources */ = {isa = PBXBuildFile; fileRef = F060606060606060606060606 /* MockTradingBackend.swift */; };
		B070707070707070707070707 /* TradingStore.swift in Sources */ = {isa = PBXBuildFile; fileRef = F070707070707070707070707 /* TradingStore.swift */; };
		B080808080808080808080808 /* MainTabView.swift in Sources */ = {isa = PBXBuildFile; fileRef = F080808080808080808080808 /* MainTabView.swift */; };
		B090909090909090909090909 /* TradingViews.swift in Sources */ = {isa = PBXBuildFile; fileRef = F090909090909090909090909 /* TradingViews.swift */; };
		BA0A0A0A0A0A0A0A0A0A0A0A /* Assets.xcassets in Resources */ = {isa = PBXBuildFile; fileRef = FA0A0A0A0A0A0A0A0A0A0A0A /* Assets.xcassets */; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		F010101010101010101010101 /* TradingAppApp.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = TradingAppApp.swift; sourceTree = "<group>"; };
		F020202020202020202020202 /* Models.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = Models.swift; sourceTree = "<group>"; };
		F030303030303030303030303 /* CredentialStore.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = CredentialStore.swift; sourceTree = "<group>"; };
		F040404040404040404040404 /* SecureHTTPClient.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = SecureHTTPClient.swift; sourceTree = "<group>"; };
		F050505050505050505050505 /* TradingAPIClient.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = TradingAPIClient.swift; sourceTree = "<group>"; };
		F060606060606060606060606 /* MockTradingBackend.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = MockTradingBackend.swift; sourceTree = "<group>"; };
		F070707070707070707070707 /* TradingStore.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = TradingStore.swift; sourceTree = "<group>"; };
		F080808080808080808080808 /* MainTabView.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = MainTabView.swift; sourceTree = "<group>"; };
		F090909090909090909090909 /* TradingViews.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = TradingViews.swift; sourceTree = "<group>"; };
		FA0A0A0A0A0A0A0A0A0A0A0A /* Assets.xcassets */ = {isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; };
		PROD0000000000000000000001 /* TradingApp.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = TradingApp.app; sourceTree = BUILT_PRODUCTS_DIR; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		FRMW0000000000000000000001 /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		GRP0000000000000000000001 = {
			isa = PBXGroup;
			children = (
				GRP0000000000000000000002 /* TradingApp */,
				GRP0000000000000000000003 /* Products */,
			);
			sourceTree = "<group>";
		};
		GRP0000000000000000000002 /* TradingApp */ = {
			isa = PBXGroup;
			children = (
				F010101010101010101010101 /* TradingAppApp.swift */,
				F020202020202020202020202 /* Models.swift */,
				F030303030303030303030303 /* CredentialStore.swift */,
				F040404040404040404040404 /* SecureHTTPClient.swift */,
				F050505050505050505050505 /* TradingAPIClient.swift */,
				F060606060606060606060606 /* MockTradingBackend.swift */,
				F070707070707070707070707 /* TradingStore.swift */,
				F080808080808080808080808 /* MainTabView.swift */,
				F090909090909090909090909 /* TradingViews.swift */,
				FA0A0A0A0A0A0A0A0A0A0A0A /* Assets.xcassets */,
			);
			path = TradingApp;
			sourceTree = "<group>";
		};
		GRP0000000000000000000003 /* Products */ = {
			isa = PBXGroup;
			children = (
				PROD0000000000000000000001 /* TradingApp.app */,
			);
			name = Products;
			sourceTree = "<group>";
		};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		TGT0000000000000000000001 /* TradingApp */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = CFG0000000000000000000003 /* Build configuration list for PBXNativeTarget "TradingApp" */;
			buildPhases = (
				SRCS0000000000000000000001 /* Sources */,
				FRMW0000000000000000000001 /* Frameworks */,
				RESS0000000000000000000001 /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = TradingApp;
			productName = TradingApp;
			productReference = PROD0000000000000000000001 /* TradingApp.app */;
			productType = "com.apple.product-type.application";
		};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		PRJ0000000000000000000001 /* Project object */ = {
			isa = PBXProject;
			attributes = {
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1500;
				LastUpgradeCheck = 1500;
				TargetAttributes = {
					TGT0000000000000000000001 = {
						CreatedOnToolsVersion = 15.0;
					};
				};
			};
			buildConfigurationList = CFG0000000000000000000001 /* Build configuration list for PBXProject "TradingApp" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = GRP0000000000000000000001;
			productRefGroup = GRP0000000000000000000003 /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				TGT0000000000000000000001 /* TradingApp */,
			);
		};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		RESS0000000000000000000001 /* Resources */ = {
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				BA0A0A0A0A0A0A0A0A0A0A0A /* Assets.xcassets in Resources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		SRCS0000000000000000000001 /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				B010101010101010101010101 /* TradingAppApp.swift in Sources */,
				B020202020202020202020202 /* Models.swift in Sources */,
				B030303030303030303030303 /* CredentialStore.swift in Sources */,
				B040404040404040404040404 /* SecureHTTPClient.swift in Sources */,
				B050505050505050505050505 /* TradingAPIClient.swift in Sources */,
				B060606060606060606060606 /* MockTradingBackend.swift in Sources */,
				B070707070707070707070707 /* TradingStore.swift in Sources */,
				B080808080808080808080808 /* MainTabView.swift in Sources */,
				B090909090909090909090909 /* TradingViews.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		CFG0000000000000000000011 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
				CLANG_WARN_BOOL_CONVERSION = YES;
				CLANG_WARN_COMMA = YES;
				CLANG_WARN_CONSTANT_CONVERSION = YES;
				CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
				CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
				CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
				CLANG_WARN_EMPTY_BODY = YES;
				CLANG_WARN_ENUM_CONVERSION = YES;
				CLANG_WARN_INFINITE_RECURSION = YES;
				CLANG_WARN_INT_CONVERSION = YES;
				CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
				CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
				CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
				CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
				CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
				CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
				CLANG_WARN_STRICT_PROTOTYPES = YES;
				CLANG_WARN_SUSPICIOUS_MOVE = YES;
				CLANG_WARN_UNGUARDED_AVAILABILITY = YES_AGGRESSIVE;
				CLANG_WARN_UNREACHABLE_CODE = YES;
				CLANG_WARN__DUPLICATE_METHOD_MATCH = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_TESTABILITY = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = YES;
				GCC_C_LANGUAGE_STANDARD = gnu17;
				GCC_DYNAMIC_NO_PIC = NO;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
				GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
				GCC_WARN_UNDECLARED_SELECTOR = YES;
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				GCC_WARN_UNUSED_FUNCTION = YES;
				GCC_WARN_UNUSED_VARIABLE = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				LOCALIZATION_PREFERS_STRING_CATALOGS = YES;
				MTL_ENABLE_DEBUG_INFO = INCLUDE_SOURCE;
				MTL_FAST_MATH = YES;
				ONLY_ACTIVE_ARCH = YES;
				SDKROOT = iphoneos;
				SWIFT_ACTIVE_COMPILATION_CONDITIONS = "DEBUG $(inherited)";
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
			};
			name = Debug;
		};
		CFG0000000000000000000012 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;
				CLANG_ANALYZER_NONNULL = YES;
				CLANG_ANALYZER_NUMBER_OBJECT_CONVERSION = YES_AGGRESSIVE;
				CLANG_CXX_LANGUAGE_STANDARD = "gnu++20";
				CLANG_ENABLE_MODULES = YES;
				CLANG_ENABLE_OBJC_ARC = YES;
				CLANG_ENABLE_OBJC_WEAK = YES;
				CLANG_WARN_BLOCK_CAPTURE_AUTORELEASING = YES;
				CLANG_WARN_BOOL_CONVERSION = YES;
				CLANG_WARN_COMMA = YES;
				CLANG_WARN_CONSTANT_CONVERSION = YES;
				CLANG_WARN_DEPRECATED_OBJC_IMPLEMENTATIONS = YES;
				CLANG_WARN_DIRECT_OBJC_ISA_USAGE = YES_ERROR;
				CLANG_WARN_DOCUMENTATION_COMMENTS = YES;
				CLANG_WARN_EMPTY_BODY = YES;
				CLANG_WARN_ENUM_CONVERSION = YES;
				CLANG_WARN_INFINITE_RECURSION = YES;
				CLANG_WARN_INT_CONVERSION = YES;
				CLANG_WARN_NON_LITERAL_NULL_CONVERSION = YES;
				CLANG_WARN_OBJC_IMPLICIT_RETAIN_SELF = YES;
				CLANG_WARN_OBJC_LITERAL_CONVERSION = YES;
				CLANG_WARN_OBJC_ROOT_CLASS = YES_ERROR;
				CLANG_WARN_QUOTED_INCLUDE_IN_FRAMEWORK_HEADER = YES;
				CLANG_WARN_RANGE_LOOP_ANALYSIS = YES;
				CLANG_WARN_STRICT_PROTOTYPES = YES;
				CLANG_WARN_SUSPICIOUS_MOVE = YES;
				CLANG_WARN_UNGUARDED_AVAILABILITY = YES_AGGRESSIVE;
				CLANG_WARN_UNREACHABLE_CODE = YES;
				CLANG_WARN__DUPLICATE_METHOD_MATCH = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				ENABLE_USER_SCRIPT_SANDBOXING = YES;
				GCC_C_LANGUAGE_STANDARD = gnu17;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_WARN_64_TO_32_BIT_CONVERSION = YES;
				GCC_WARN_ABOUT_RETURN_TYPE = YES_ERROR;
				GCC_WARN_UNDECLARED_SELECTOR = YES;
				GCC_WARN_UNINITIALIZED_AUTOS = YES_AGGRESSIVE;
				GCC_WARN_UNUSED_FUNCTION = YES;
				GCC_WARN_UNUSED_VARIABLE = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				LOCALIZATION_PREFERS_STRING_CATALOGS = YES;
				MTL_ENABLE_DEBUG_INFO = NO;
				MTL_FAST_MATH = YES;
				SDKROOT = iphoneos;
				SWIFT_COMPILATION_MODE = wholemodule;
				VALIDATE_PRODUCT = YES;
			};
			name = Release;
		};
		CFG0000000000000000000021 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				DEVELOPMENT_TEAM = "";
				ENABLE_PREVIEWS = YES;
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_KEY_CFBundleDisplayName = Trading;
				INFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.finance";
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				INFOPLIST_KEY_UISupportedInterfaceOrientations = UIInterfaceOrientationPortrait;
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = "UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.tradingapp.TradingApp;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_STRICT_CONCURRENCY = complete;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Debug;
		};
		CFG0000000000000000000022 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ASSETCATALOG_COMPILER_GLOBAL_ACCENT_COLOR_NAME = AccentColor;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				DEVELOPMENT_TEAM = "";
				ENABLE_PREVIEWS = YES;
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_KEY_CFBundleDisplayName = Trading;
				INFOPLIST_KEY_LSApplicationCategoryType = "public.app-category.finance";
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				INFOPLIST_KEY_UISupportedInterfaceOrientations = UIInterfaceOrientationPortrait;
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPad = "UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight UIInterfaceOrientationPortrait UIInterfaceOrientationPortraitUpsideDown";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.tradingapp.TradingApp;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_STRICT_CONCURRENCY = complete;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Release;
		};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		CFG0000000000000000000001 /* Build configuration list for PBXProject "TradingApp" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				CFG0000000000000000000011 /* Debug */,
				CFG0000000000000000000012 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		CFG0000000000000000000003 /* Build configuration list for PBXNativeTarget "TradingApp" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				CFG0000000000000000000021 /* Debug */,
				CFG0000000000000000000022 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
/* End XCConfigurationList section */
	};
	rootObject = PRJ0000000000000000000001 /* Project object */;
}

<<<FILE TradingApp/TradingApp.xcodeproj/xcshareddata/xcschemes/TradingApp.xcscheme>>>
<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1500"
   version = "1.7">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "TGT0000000000000000000001"
               BuildableName = "TradingApp.app"
               BlueprintName = "TradingApp"
               ReferencedContainer = "container:TradingApp.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES"
      shouldAutocreateTestPlan = "YES">
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "TGT0000000000000000000001"
            BuildableName = "TradingApp.app"
            BlueprintName = "TradingApp"
            ReferencedContainer = "container:TradingApp.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "TGT0000000000000000000001"
            BuildableName = "TradingApp.app"
            BlueprintName = "TradingApp"
            ReferencedContainer = "container:TradingApp.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>

`</think>`
``

The runnable project is under `TradingApp/` in your workspace (Swift sources, `project.pbxproj`, shared `TradingApp.xcscheme`, assets). `ASSETCATALOG_COMPILER_APPICON_NAME` was removed so the target builds without an App Icon image set.

The message above is the full multi-file dump you asked for (delimiter lines only, no markdown or prose).