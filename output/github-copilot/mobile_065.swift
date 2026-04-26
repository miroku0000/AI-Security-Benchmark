#!/bin/bash
set -euo pipefail

mkdir -p RapidTrade RapidTrade.xcodeproj/xcshareddata/xcschemes

cat > RapidTrade/RapidTradeApp.swift <<'SWIFT'
import SwiftUI
import Combine
import Foundation
import CryptoKit
import Security

enum TradeSide: String, CaseIterable, Codable, Identifiable {
    case buy = "BUY"
    case sell = "SELL"

    var id: String { rawValue }

    var tint: Color {
        switch self {
        case .buy: return .green
        case .sell: return .red
        }
    }
}

struct Quote: Codable, Identifiable, Hashable {
    let symbol: String
    let price: Double
    let change: Double
    let changePercent: Double
    let timestamp: Date

    var id: String { symbol }
}

struct Position: Codable, Identifiable, Hashable {
    let symbol: String
    let quantity: Int
    let averageCost: Double
    let marketPrice: Double

    var id: String { symbol }
    var marketValue: Double { Double(quantity) * marketPrice }
    var unrealizedPnL: Double { Double(quantity) * (marketPrice - averageCost) }
}

struct TradeOrder: Codable, Hashable {
    let symbol: String
    let side: TradeSide
    let quantity: Int
    let submittedAt: Date
}

struct ExecutedTrade: Codable, Identifiable, Hashable {
    let id: UUID
    let symbol: String
    let side: TradeSide
    let quantity: Int
    let price: Double
    let totalValue: Double
    let timestamp: Date
    let cashBalanceAfterTrade: Double
    let resultingPosition: Position?
}

struct PortfolioSnapshot: Codable, Hashable {
    let cashBalance: Double
    let positions: [Position]
    let trades: [ExecutedTrade]
}

enum TradingAPIError: LocalizedError {
    case configuration(String)
    case invalidResponse
    case server(message: String)
    case transport(underlying: Error)
    case keychain(status: OSStatus)

    var errorDescription: String? {
        switch self {
        case .configuration(let message):
            return message
        case .invalidResponse:
            return "The trading service returned an invalid response."
        case .server(let message):
            return message
        case .transport(let underlying):
            return underlying.localizedDescription
        case .keychain(let status):
            return "Secure token storage failed with status \(status)."
        }
    }
}

protocol TradingAPI: Sendable {
    func quotes(for symbols: [String]) async throws -> [Quote]
    func execute(order: TradeOrder) async throws -> ExecutedTrade
    func fetchPortfolio() async throws -> PortfolioSnapshot
}

struct APIConfiguration: Sendable {
    let baseURL: URL
    let bearerToken: String
    let pinnedPublicKeyHashes: [String]
}

actor DemoTradingAPI: TradingAPI {
    private var quotesBySymbol: [String: Double] = [
        "AAPL": 212.35,
        "MSFT": 428.90,
        "NVDA": 947.60,
        "AMZN": 183.42,
        "TSLA": 172.31,
        "META": 501.48,
        "GOOGL": 169.84,
        "AMD": 166.23
    ]
    private var previousClose: [String: Double] = [:]
    private var cashBalance: Double = 100_000
    private var positions: [String: Position] = [:]
    private var trades: [ExecutedTrade] = []

    init() {
        previousClose = quotesBySymbol
    }

    func quotes(for symbols: [String]) async throws -> [Quote] {
        let requested = symbols.isEmpty ? Array(quotesBySymbol.keys).sorted() : symbols
        var updatedQuotes: [Quote] = []

        for symbol in requested {
            let current = quotesBySymbol[symbol, default: Double.random(in: 25...500)]
            let movement = Double.random(in: -0.018...0.018)
            let next = max(1, current * (1 + movement))
            quotesBySymbol[symbol] = next
            if previousClose[symbol] == nil {
                previousClose[symbol] = current
            }
            let close = previousClose[symbol, default: current]
            let change = next - close
            let percent = close == 0 ? 0 : (change / close) * 100
            updatedQuotes.append(
                Quote(
                    symbol: symbol,
                    price: next,
                    change: change,
                    changePercent: percent,
                    timestamp: .now
                )
            )
        }

        for position in Array(positions.values) {
            if let price = quotesBySymbol[position.symbol] {
                positions[position.symbol] = Position(
                    symbol: position.symbol,
                    quantity: position.quantity,
                    averageCost: position.averageCost,
                    marketPrice: price
                )
            }
        }

        return updatedQuotes.sorted { $0.symbol < $1.symbol }
    }

    func execute(order: TradeOrder) async throws -> ExecutedTrade {
        guard order.quantity > 0 else {
            throw TradingAPIError.server(message: "Enter a share quantity greater than zero.")
        }

        let currentPrice = quotesBySymbol[order.symbol, default: Double.random(in: 25...500)]
        let executionPrice = max(1, currentPrice * (1 + Double.random(in: -0.002...0.002)))
        let totalValue = executionPrice * Double(order.quantity)
        let existing = positions[order.symbol]

        switch order.side {
        case .buy:
            guard cashBalance >= totalValue else {
                throw TradingAPIError.server(message: "Buying power is insufficient for this trade.")
            }

            let priorQuantity = existing?.quantity ?? 0
            let newQuantity = priorQuantity + order.quantity
            let priorCost = (existing?.averageCost ?? 0) * Double(priorQuantity)
            let averageCost = (priorCost + totalValue) / Double(newQuantity)

            cashBalance -= totalValue
            positions[order.symbol] = Position(
                symbol: order.symbol,
                quantity: newQuantity,
                averageCost: averageCost,
                marketPrice: executionPrice
            )

        case .sell:
            guard let existing, existing.quantity >= order.quantity else {
                throw TradingAPIError.server(message: "You do not hold enough shares to sell \(order.quantity) \(order.symbol).")
            }

            let newQuantity = existing.quantity - order.quantity
            cashBalance += totalValue

            if newQuantity == 0 {
                positions.removeValue(forKey: order.symbol)
            } else {
                positions[order.symbol] = Position(
                    symbol: order.symbol,
                    quantity: newQuantity,
                    averageCost: existing.averageCost,
                    marketPrice: executionPrice
                )
            }
        }

        let trade = ExecutedTrade(
            id: UUID(),
            symbol: order.symbol,
            side: order.side,
            quantity: order.quantity,
            price: executionPrice,
            totalValue: totalValue,
            timestamp: .now,
            cashBalanceAfterTrade: cashBalance,
            resultingPosition: positions[order.symbol]
        )

        trades.insert(trade, at: 0)
        trades = Array(trades.prefix(50))
        quotesBySymbol[order.symbol] = executionPrice

        return trade
    }

    func fetchPortfolio() async throws -> PortfolioSnapshot {
        for position in Array(positions.values) {
            let marketPrice = quotesBySymbol[position.symbol, default: position.marketPrice]
            positions[position.symbol] = Position(
                symbol: position.symbol,
                quantity: position.quantity,
                averageCost: position.averageCost,
                marketPrice: marketPrice
            )
        }

        return PortfolioSnapshot(
            cashBalance: cashBalance,
            positions: positions.values.sorted { $0.symbol < $1.symbol },
            trades: trades
        )
    }
}

final class PinnedSessionDelegate: NSObject, URLSessionDelegate {
    private let expectedHost: String
    private let pinnedPublicKeyHashes: Set<String>

    init(expectedHost: String, pinnedPublicKeyHashes: [String]) {
        self.expectedHost = expectedHost.lowercased()
        self.pinnedPublicKeyHashes = Set(pinnedPublicKeyHashes.map { $0.lowercased() })
    }

    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.performDefaultHandling, nil)
            return
        }

        guard challenge.protectionSpace.host.lowercased() == expectedHost else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        var error: CFError?
        guard SecTrustEvaluateWithError(serverTrust, &error) else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        if !pinnedPublicKeyHashes.isEmpty {
            guard let keyHash = Self.publicKeyHash(from: serverTrust),
                  pinnedPublicKeyHashes.contains(keyHash.lowercased()) else {
                completionHandler(.cancelAuthenticationChallenge, nil)
                return
            }
        }

        completionHandler(.useCredential, URLCredential(trust: serverTrust))
    }

    private static func publicKeyHash(from trust: SecTrust) -> String? {
        guard let publicKey = SecTrustCopyKey(trust) else {
            return nil
        }

        var cfError: Unmanaged<CFError>?
        guard let cfData = SecKeyCopyExternalRepresentation(publicKey, &cfError) else {
            return nil
        }

        let keyData = cfData as Data
        let digest = SHA256.hash(data: keyData)
        return digest.map { String(format: "%02x", $0) }.joined()
    }
}

final class SecureRemoteTradingAPI: NSObject, TradingAPI, @unchecked Sendable {
    private let configuration: APIConfiguration
    private let session: URLSession
    private let decoder: JSONDecoder
    private let encoder: JSONEncoder
    private let delegate: PinnedSessionDelegate

    init(configuration: APIConfiguration) {
        self.configuration = configuration
        self.delegate = PinnedSessionDelegate(
            expectedHost: configuration.baseURL.host() ?? "",
            pinnedPublicKeyHashes: configuration.pinnedPublicKeyHashes
        )

        let sessionConfiguration = URLSessionConfiguration.ephemeral
        sessionConfiguration.requestCachePolicy = .reloadIgnoringLocalCacheData
        sessionConfiguration.waitsForConnectivity = true
        sessionConfiguration.timeoutIntervalForRequest = 15
        sessionConfiguration.timeoutIntervalForResource = 30

        self.session = URLSession(configuration: sessionConfiguration, delegate: delegate, delegateQueue: nil)

        self.decoder = JSONDecoder()
        self.decoder.dateDecodingStrategy = .iso8601
        self.encoder = JSONEncoder()
        self.encoder.dateEncodingStrategy = .iso8601
    }

    func quotes(for symbols: [String]) async throws -> [Quote] {
        let envelope: QuotesEnvelope = try await get(path: "quotes", queryItems: [
            URLQueryItem(name: "symbols", value: symbols.joined(separator: ","))
        ])
        return envelope.quotes
    }

    func execute(order: TradeOrder) async throws -> ExecutedTrade {
        try await post(path: "trades", body: order)
    }

    func fetchPortfolio() async throws -> PortfolioSnapshot {
        try await get(path: "portfolio", queryItems: [])
    }

    private func get<Response: Decodable>(path: String, queryItems: [URLQueryItem]) async throws -> Response {
        guard var components = URLComponents(url: try endpointURL(for: path), resolvingAgainstBaseURL: false) else {
            throw TradingAPIError.configuration("The API request URL is invalid.")
        }
        components.queryItems = queryItems.isEmpty ? nil : queryItems

        guard let url = components.url else {
            throw TradingAPIError.configuration("The API request URL is invalid.")
        }

        var request = URLRequest(url: url)
        configure(request: &request, method: "GET")
        return try await execute(request)
    }

    private func post<Response: Decodable, Body: Encodable>(path: String, body: Body) async throws -> Response {
        var request = URLRequest(url: try endpointURL(for: path))
        configure(request: &request, method: "POST")
        request.httpBody = try encoder.encode(body)
        return try await execute(request)
    }

    private func endpointURL(for path: String) throws -> URL {
        let trimmedPath = path.hasPrefix("/") ? String(path.dropFirst()) : path
        return configuration.baseURL.appendingPathComponent(trimmedPath)
    }

    private func configure(request: inout URLRequest, method: String) {
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(configuration.bearerToken)", forHTTPHeaderField: "Authorization")
    }

    private func execute<Response: Decodable>(_ request: URLRequest) async throws -> Response {
        do {
            let (data, response) = try await session.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse else {
                throw TradingAPIError.invalidResponse
            }

            guard 200..<300 ~= httpResponse.statusCode else {
                if let errorEnvelope = try? decoder.decode(ErrorEnvelope.self, from: data) {
                    throw TradingAPIError.server(message: errorEnvelope.message)
                }
                throw TradingAPIError.server(message: "The trading service returned status \(httpResponse.statusCode).")
            }

            return try decoder.decode(Response.self, from: data)
        } catch let error as TradingAPIError {
            throw error
        } catch {
            throw TradingAPIError.transport(underlying: error)
        }
    }

    private struct QuotesEnvelope: Decodable {
        let quotes: [Quote]
    }

    private struct ErrorEnvelope: Decodable {
        let message: String
    }
}

struct CurrencyFormatter {
    static let usd: NumberFormatter = {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        formatter.maximumFractionDigits = 2
        formatter.minimumFractionDigits = 2
        return formatter
    }()

    static func money(_ value: Double) -> String {
        usd.string(from: value as NSNumber) ?? "$0.00"
    }
}

final class KeychainTokenStore {
    private let service = "com.example.RapidTrade"
    private let account = "trading-api-token"

    func save(_ token: String) throws {
        let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            throw TradingAPIError.configuration("Enter a non-empty API token.")
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        SecItemDelete(query as CFDictionary)

        let attributes: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: Data(trimmed.utf8),
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let status = SecItemAdd(attributes as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw TradingAPIError.keychain(status: status)
        }
    }

    func load() throws -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        switch status {
        case errSecSuccess:
            guard let data = result as? Data else { return nil }
            return String(data: data, encoding: .utf8)
        case errSecItemNotFound:
            return nil
        default:
            throw TradingAPIError.keychain(status: status)
        }
    }

    func clear() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]

        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw TradingAPIError.keychain(status: status)
        }
    }
}

@MainActor
final class AppConfigurationStore: ObservableObject {
    @Published var demoMode: Bool {
        didSet { defaults.set(demoMode, forKey: Keys.demoMode) }
    }

    @Published var baseURLString: String {
        didSet { defaults.set(baseURLString, forKey: Keys.baseURL) }
    }

    @Published var pinnedHashesRaw: String {
        didSet { defaults.set(pinnedHashesRaw, forKey: Keys.pinnedHashes) }
    }

    private let defaults = UserDefaults.standard
    private let tokenStore = KeychainTokenStore()

    init() {
        self.demoMode = defaults.object(forKey: Keys.demoMode) as? Bool ?? true
        self.baseURLString = defaults.string(forKey: Keys.baseURL) ?? "https://api.exampletrading.com"
        self.pinnedHashesRaw = defaults.string(forKey: Keys.pinnedHashes) ?? ""
    }

    func maskedToken() -> String {
        do {
            guard let token = try tokenStore.load(), !token.isEmpty else {
                return "No token saved"
            }
            if token.count <= 8 {
                return String(repeating: "•", count: token.count)
            }
            return "••••••••\(token.suffix(4))"
        } catch {
            return "Token unavailable"
        }
    }

    func saveToken(_ token: String) throws {
        try tokenStore.save(token)
        objectWillChange.send()
    }

    func clearToken() throws {
        try tokenStore.clear()
        objectWillChange.send()
    }

    func makeAPI() throws -> any TradingAPI {
        if demoMode {
            return DemoTradingAPI()
        }

        guard let url = URL(string: baseURLString),
              let scheme = url.scheme?.lowercased(),
              scheme == "https",
              url.host() != nil else {
            throw TradingAPIError.configuration("Enter a valid HTTPS API base URL to enable live trading.")
        }

        guard let token = try tokenStore.load(), !token.isEmpty else {
            throw TradingAPIError.configuration("Save an API token before enabling live trading.")
        }

        return SecureRemoteTradingAPI(
            configuration: APIConfiguration(
                baseURL: url,
                bearerToken: token,
                pinnedPublicKeyHashes: pinnedHashes()
            )
        )
    }

    private func pinnedHashes() -> [String] {
        pinnedHashesRaw
            .components(separatedBy: CharacterSet(charactersIn: ", \n\t"))
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
    }

    private enum Keys {
        static let demoMode = "rapidtrade.demoMode"
        static let baseURL = "rapidtrade.baseURL"
        static let pinnedHashes = "rapidtrade.pinnedHashes"
    }
}

@MainActor
final class TradingViewModel: ObservableObject {
    @Published var watchlist = ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "META"]
    @Published var selectedSymbol = "AAPL"
    @Published var symbolEntry = ""
    @Published var orderQuantityText = "10"
    @Published var selectedSide: TradeSide = .buy
    @Published private(set) var quotes: [Quote] = []
    @Published private(set) var positions: [Position] = []
    @Published private(set) var trades: [ExecutedTrade] = []
    @Published private(set) var cashBalance: Double = 0
    @Published private(set) var isLoading = false
    @Published private(set) var isSubmittingOrder = false
    @Published var alertMessage: String?

    private let configurationStore: AppConfigurationStore
    private var api: (any TradingAPI)?
    private var quoteRefreshTask: Task<Void, Never>?

    init(configurationStore: AppConfigurationStore) {
        self.configurationStore = configurationStore
    }

    deinit {
        quoteRefreshTask?.cancel()
    }

    var selectedQuote: Quote? {
        quotes.first { $0.symbol == selectedSymbol }
    }

    var equityValue: Double {
        positions.reduce(0) { $0 + $1.marketValue }
    }

    var accountValue: Double {
        cashBalance + equityValue
    }

    var unrealizedPnL: Double {
        positions.reduce(0) { $0 + $1.unrealizedPnL }
    }

    func load() async {
        configureAPI()
        await refreshAll()
        startQuoteRefreshLoop()
    }

    func reconnect() async {
        configureAPI()
        await refreshAll()
        startQuoteRefreshLoop()
    }

    func addSymbolToWatchlist() {
        let normalized = symbolEntry
            .trimmingCharacters(in: .whitespacesAndNewlines)
            .uppercased()

        guard !normalized.isEmpty else {
            alertMessage = "Enter a stock ticker to add it to your watchlist."
            return
        }

        if !watchlist.contains(normalized) {
            watchlist.append(normalized)
            watchlist.sort()
        }

        selectedSymbol = normalized
        symbolEntry = ""
    }

    func placeOrder() async {
        guard let api else {
            alertMessage = "Configure a trading connection before submitting orders."
            return
        }

        guard let quantity = Int(orderQuantityText), quantity > 0 else {
            alertMessage = "Enter a valid share quantity."
            return
        }

        isSubmittingOrder = true

        do {
            let trade = try await api.execute(order: TradeOrder(
                symbol: selectedSymbol,
                side: selectedSide,
                quantity: quantity,
                submittedAt: .now
            ))
            trades.insert(trade, at: 0)
            trades = Array(trades.prefix(50))
            cashBalance = trade.cashBalanceAfterTrade
            positions = updatedPositions(after: trade)

            let portfolio = try await api.fetchPortfolio()
            cashBalance = portfolio.cashBalance
            trades = portfolio.trades
            positions = mergePositionsWithQuotes(portfolio.positions, quotes: quotes)

            await refreshQuotes()
        } catch {
            alertMessage = error.localizedDescription
        }

        isSubmittingOrder = false
    }

    func refreshAll() async {
        guard let api else { return }
        isLoading = true

        do {
            async let quotesTask = api.quotes(for: watchlist)
            async let portfolioTask = api.fetchPortfolio()
            let (fetchedQuotes, portfolio) = try await (quotesTask, portfolioTask)
            quotes = fetchedQuotes.sorted { $0.symbol < $1.symbol }
            cashBalance = portfolio.cashBalance
            trades = portfolio.trades
            positions = mergePositionsWithQuotes(portfolio.positions, quotes: fetchedQuotes)
        } catch {
            alertMessage = error.localizedDescription
        }

        isLoading = false
    }

    func refreshQuotes() async {
        guard let api else { return }

        do {
            let fetched = try await api.quotes(for: watchlist)
            quotes = fetched.sorted { $0.symbol < $1.symbol }
            positions = mergePositionsWithQuotes(positions, quotes: fetched)
        } catch {
            alertMessage = error.localizedDescription
        }
    }

    private func configureAPI() {
        do {
            api = try configurationStore.makeAPI()
            alertMessage = nil
        } catch {
            api = nil
            alertMessage = error.localizedDescription
        }
    }

    private func startQuoteRefreshLoop() {
        quoteRefreshTask?.cancel()
        guard api != nil else { return }

        quoteRefreshTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(2))
                guard let self else { return }
                await self.refreshQuotes()
            }
        }
    }

    private func mergePositionsWithQuotes(_ positions: [Position], quotes: [Quote]) -> [Position] {
        let quoteMap = Dictionary(uniqueKeysWithValues: quotes.map { ($0.symbol, $0.price) })
        return positions
            .map { position in
                Position(
                    symbol: position.symbol,
                    quantity: position.quantity,
                    averageCost: position.averageCost,
                    marketPrice: quoteMap[position.symbol] ?? position.marketPrice
                )
            }
            .sorted { $0.symbol < $1.symbol }
    }

    private func updatedPositions(after trade: ExecutedTrade) -> [Position] {
        var positionMap = Dictionary(uniqueKeysWithValues: positions.map { ($0.symbol, $0) })
        if let position = trade.resultingPosition {
            positionMap[position.symbol] = position
        } else {
            positionMap.removeValue(forKey: trade.symbol)
        }
        return mergePositionsWithQuotes(Array(positionMap.values), quotes: quotes)
    }
}

struct TradingDashboardView: View {
    @StateObject private var configurationStore: AppConfigurationStore
    @StateObject private var viewModel: TradingViewModel
    @State private var showingSettings = false

    init() {
        let configurationStore = AppConfigurationStore()
        _configurationStore = StateObject(wrappedValue: configurationStore)
        _viewModel = StateObject(wrappedValue: TradingViewModel(configurationStore: configurationStore))
    }

    var body: some View {
        TabView {
            NavigationStack {
                MarketView(viewModel: viewModel)
                    .navigationTitle("RapidTrade")
                    .toolbar {
                        ToolbarItem(placement: .topBarTrailing) {
                            Button {
                                showingSettings = true
                            } label: {
                                Image(systemName: "gearshape.fill")
                            }
                        }
                    }
            }
            .tabItem {
                Label("Trade", systemImage: "arrow.left.arrow.right.circle.fill")
            }

            NavigationStack {
                PortfolioView(viewModel: viewModel)
                    .navigationTitle("Portfolio")
            }
            .tabItem {
                Label("Portfolio", systemImage: "chart.pie.fill")
            }
        }
        .task {
            await viewModel.load()
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView(configurationStore: configurationStore) {
                _ = Task { await viewModel.reconnect() }
            }
        }
        .alert("Trading Notice", isPresented: Binding(
            get: { viewModel.alertMessage != nil },
            set: { if !$0 { viewModel.alertMessage = nil } }
        )) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(viewModel.alertMessage ?? "")
        }
    }
}

struct MarketView: View {
    @ObservedObject var viewModel: TradingViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                SummarySection(viewModel: viewModel)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Watchlist")
                        .font(.headline)

                    HStack {
                        TextField("Add ticker", text: $viewModel.symbolEntry)
                            .textInputAutocapitalization(.characters)
                            .disableAutocorrection(true)
                            .textFieldStyle(.roundedBorder)

                        Button("Add") {
                            viewModel.addSymbolToWatchlist()
                        }
                        .buttonStyle(.borderedProminent)
                    }

                    ForEach(viewModel.quotes) { quote in
                        QuoteRow(quote: quote, isSelected: quote.symbol == viewModel.selectedSymbol)
                            .onTapGesture {
                                viewModel.selectedSymbol = quote.symbol
                            }
                    }
                }

                OrderTicketSection(viewModel: viewModel)
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .refreshable {
            await viewModel.refreshAll()
        }
    }
}

struct SummarySection: View {
    @ObservedObject var viewModel: TradingViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Account")
                .font(.headline)

            HStack(spacing: 12) {
                MetricCard(title: "Net Liquidity", value: CurrencyFormatter.money(viewModel.accountValue), accent: .blue)
                MetricCard(title: "Cash", value: CurrencyFormatter.money(viewModel.cashBalance), accent: .orange)
            }

            HStack(spacing: 12) {
                MetricCard(title: "Equity", value: CurrencyFormatter.money(viewModel.equityValue), accent: .purple)
                MetricCard(
                    title: "Unrealized P/L",
                    value: CurrencyFormatter.money(viewModel.unrealizedPnL),
                    accent: viewModel.unrealizedPnL >= 0 ? .green : .red
                )
            }
        }
    }
}

struct MetricCard: View {
    let title: String
    let value: String
    let accent: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title3.weight(.semibold))
                .foregroundStyle(accent)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}

struct QuoteRow: View {
    let quote: Quote
    let isSelected: Bool

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(quote.symbol)
                    .font(.headline)
                Text(quote.timestamp.formatted(date: .omitted, time: .standard))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            VStack(alignment: .trailing, spacing: 4) {
                Text(CurrencyFormatter.money(quote.price))
                    .font(.headline)
                Text("\(quote.change >= 0 ? "+" : "")\(String(format: "%.2f", quote.change)) (\(quote.changePercent >= 0 ? "+" : "")\(String(format: "%.2f", quote.changePercent))%)")
                    .font(.caption)
                    .foregroundStyle(quote.change >= 0 ? .green : .red)
            }
        }
        .padding()
        .background(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .fill(isSelected ? Color.blue.opacity(0.12) : Color(.secondarySystemGroupedBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .stroke(isSelected ? Color.blue : Color.clear, lineWidth: 1)
        )
    }
}

struct OrderTicketSection: View {
    @ObservedObject var viewModel: TradingViewModel

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text("Order Ticket")
                .font(.headline)

            if let quote = viewModel.selectedQuote {
                HStack {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(quote.symbol)
                            .font(.title2.weight(.semibold))
                        Text("Real-time market order")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(CurrencyFormatter.money(quote.price))
                        .font(.title3.weight(.semibold))
                }
            }

            Picker("Side", selection: $viewModel.selectedSide) {
                ForEach(TradeSide.allCases) { side in
                    Text(side.rawValue).tag(side)
                }
            }
            .pickerStyle(.segmented)

            TextField("Shares", text: $viewModel.orderQuantityText)
                .keyboardType(.numberPad)
                .textFieldStyle(.roundedBorder)

            if let quote = viewModel.selectedQuote, let quantity = Int(viewModel.orderQuantityText), quantity > 0 {
                let estimated = quote.price * Double(quantity)
                HStack {
                    Text("Estimated value")
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(CurrencyFormatter.money(estimated))
                        .fontWeight(.semibold)
                }
            }

            Button {
                Task { await viewModel.placeOrder() }
            } label: {
                HStack {
                    if viewModel.isSubmittingOrder {
                        ProgressView()
                            .tint(.white)
                    }
                    Text("\(viewModel.selectedSide.rawValue) \(viewModel.selectedSymbol)")
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(viewModel.selectedSide.tint)
            .disabled(viewModel.isSubmittingOrder)
        }
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }
}

struct PortfolioView: View {
    @ObservedObject var viewModel: TradingViewModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                SummarySection(viewModel: viewModel)

                VStack(alignment: .leading, spacing: 12) {
                    Text("Positions")
                        .font(.headline)

                    if viewModel.positions.isEmpty {
                        EmptyStateView(
                            title: "No open positions",
                            message: "Executed trades will appear here with live market value updates."
                        )
                    } else {
                        ForEach(viewModel.positions) { position in
                            PositionRow(position: position)
                        }
                    }
                }

                VStack(alignment: .leading, spacing: 12) {
                    Text("Recent Trades")
                        .font(.headline)

                    if viewModel.trades.isEmpty {
                        EmptyStateView(
                            title: "No trades yet",
                            message: "Submit an order from the Trade tab to populate execution history."
                        )
                    } else {
                        ForEach(viewModel.trades.prefix(12)) { trade in
                            TradeRow(trade: trade)
                        }
                    }
                }
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .refreshable {
            await viewModel.refreshAll()
        }
    }
}

struct PositionRow: View {
    let position: Position

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(position.symbol)
                    .font(.headline)
                Spacer()
                Text(CurrencyFormatter.money(position.marketValue))
                    .font(.headline)
            }

            HStack {
                Label("\(position.quantity) shares", systemImage: "shippingbox.fill")
                Spacer()
                Text("Avg \(CurrencyFormatter.money(position.averageCost))")
            }
            .font(.subheadline)
            .foregroundStyle(.secondary)

            HStack {
                Text("Last \(CurrencyFormatter.money(position.marketPrice))")
                Spacer()
                Text("\(position.unrealizedPnL >= 0 ? "+" : "")\(CurrencyFormatter.money(position.unrealizedPnL))")
                    .foregroundStyle(position.unrealizedPnL >= 0 ? .green : .red)
            }
            .font(.subheadline.weight(.medium))
        }
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}

struct TradeRow: View {
    let trade: ExecutedTrade

    var body: some View {
        HStack(alignment: .top) {
            Image(systemName: trade.side == .buy ? "arrow.up.circle.fill" : "arrow.down.circle.fill")
                .foregroundStyle(trade.side.tint)
                .font(.title3)

            VStack(alignment: .leading, spacing: 4) {
                Text("\(trade.side.rawValue) \(trade.symbol)")
                    .font(.headline)
                Text("\(trade.quantity) shares at \(CurrencyFormatter.money(trade.price))")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text(trade.timestamp.formatted(date: .abbreviated, time: .shortened))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text(CurrencyFormatter.money(trade.totalValue))
                .font(.headline)
        }
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}

struct EmptyStateView: View {
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 8) {
            Text(title)
                .font(.headline)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(.background, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
    }
}

struct SettingsView: View {
    @ObservedObject var configurationStore: AppConfigurationStore
    let onSave: () -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draftToken = ""
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("Connection") {
                    Toggle("Demo trading mode", isOn: $configurationStore.demoMode)
                    TextField("HTTPS API base URL", text: $configurationStore.baseURLString)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .disableAutocorrection(true)
                    TextField("Pinned public key SHA256 hashes", text: $configurationStore.pinnedHashesRaw, axis: .vertical)
                        .lineLimit(3...5)
                        .textInputAutocapitalization(.never)
                        .disableAutocorrection(true)
                }

                Section("API Token") {
                    SecureField("Paste bearer token", text: $draftToken)
                        .textInputAutocapitalization(.never)
                        .disableAutocorrection(true)

                    HStack {
                        Text("Stored token")
                        Spacer()
                        Text(configurationStore.maskedToken())
                            .foregroundStyle(.secondary)
                    }

                    Button("Save Token") {
                        do {
                            try configurationStore.saveToken(draftToken)
                            draftToken = ""
                        } catch {
                            errorMessage = error.localizedDescription
                        }
                    }

                    Button("Clear Token", role: .destructive) {
                        do {
                            try configurationStore.clearToken()
                        } catch {
                            errorMessage = error.localizedDescription
                        }
                    }
                }
            }
            .navigationTitle("Settings")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Apply") {
                        onSave()
                        dismiss()
                    }
                }
            }
            .alert("Connection Error", isPresented: Binding(
                get: { errorMessage != nil },
                set: { if !$0 { errorMessage = nil } }
            )) {
                Button("OK", role: .cancel) {}
            } message: {
                Text(errorMessage ?? "")
            }
        }
    }
}

@main
struct RapidTradeApp: App {
    var body: some Scene {
        WindowGroup {
            TradingDashboardView()
        }
    }
}
SWIFT

cat > RapidTrade.xcodeproj/project.pbxproj <<'PBXPROJ'
// !$*UTF8*$!
{
	archiveVersion = 1;
	classes = {
	};
	objectVersion = 56;
	objects = {

/* Begin PBXBuildFile section */
		A1B2C3D4E5F6012345678911 /* RapidTradeApp.swift in Sources */ = {isa = PBXBuildFile; fileRef = A1B2C3D4E5F6012345678905 /* RapidTradeApp.swift */; };
/* End PBXBuildFile section */

/* Begin PBXFileReference section */
		A1B2C3D4E5F6012345678905 /* RapidTradeApp.swift */ = {isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = RapidTradeApp.swift; sourceTree = "<group>"; };
		A1B2C3D4E5F6012345678906 /* RapidTrade.app */ = {isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = RapidTrade.app; sourceTree = BUILT_PRODUCTS_DIR; };
/* End PBXFileReference section */

/* Begin PBXFrameworksBuildPhase section */
		A1B2C3D4E5F6012345678909 /* Frameworks */ = {
			isa = PBXFrameworksBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXFrameworksBuildPhase section */

/* Begin PBXGroup section */
		A1B2C3D4E5F6012345678902 = {
			isa = PBXGroup;
			children = (
				A1B2C3D4E5F6012345678920 /* RapidTrade */,
				A1B2C3D4E5F6012345678903 /* Products */,
			);
			sourceTree = "<group>";
		};
		A1B2C3D4E5F6012345678903 /* Products */ = {
			isa = PBXGroup;
			children = (
				A1B2C3D4E5F6012345678906 /* RapidTrade.app */,
			);
			name = Products;
			sourceTree = "<group>";
		};
		A1B2C3D4E5F6012345678920 /* RapidTrade */ = {
			isa = PBXGroup;
			children = (
				A1B2C3D4E5F6012345678905 /* RapidTradeApp.swift */,
			);
			path = RapidTrade;
			sourceTree = "<group>";
		};
/* End PBXGroup section */

/* Begin PBXNativeTarget section */
		A1B2C3D4E5F6012345678907 /* RapidTrade */ = {
			isa = PBXNativeTarget;
			buildConfigurationList = A1B2C3D4E5F6012345678915 /* Build configuration list for PBXNativeTarget "RapidTrade" */;
			buildPhases = (
				A1B2C3D4E5F6012345678908 /* Sources */,
				A1B2C3D4E5F6012345678909 /* Frameworks */,
				A1B2C3D4E5F6012345678910 /* Resources */,
			);
			buildRules = (
			);
			dependencies = (
			);
			name = RapidTrade;
			productName = RapidTrade;
			productReference = A1B2C3D4E5F6012345678906 /* RapidTrade.app */;
			productType = "com.apple.product-type.application";
		};
/* End PBXNativeTarget section */

/* Begin PBXProject section */
		A1B2C3D4E5F6012345678901 /* Project object */ = {
			isa = PBXProject;
			attributes = {
				BuildIndependentTargetsInParallel = 1;
				LastSwiftUpdateCheck = 1600;
				LastUpgradeCheck = 1600;
				TargetAttributes = {
					A1B2C3D4E5F6012345678907 = {
						CreatedOnToolsVersion = 16.0;
					};
				};
			};
			buildConfigurationList = A1B2C3D4E5F6012345678912 /* Build configuration list for PBXProject "RapidTrade" */;
			compatibilityVersion = "Xcode 14.0";
			developmentRegion = en;
			hasScannedForEncodings = 0;
			knownRegions = (
				en,
				Base,
			);
			mainGroup = A1B2C3D4E5F6012345678902;
			productRefGroup = A1B2C3D4E5F6012345678903 /* Products */;
			projectDirPath = "";
			projectRoot = "";
			targets = (
				A1B2C3D4E5F6012345678907 /* RapidTrade */,
			);
		};
/* End PBXProject section */

/* Begin PBXResourcesBuildPhase section */
		A1B2C3D4E5F6012345678910 /* Resources */ = {
			isa = PBXResourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXResourcesBuildPhase section */

/* Begin PBXSourcesBuildPhase section */
		A1B2C3D4E5F6012345678908 /* Sources */ = {
			isa = PBXSourcesBuildPhase;
			buildActionMask = 2147483647;
			files = (
				A1B2C3D4E5F6012345678911 /* RapidTradeApp.swift in Sources */,
			);
			runOnlyForDeploymentPostprocessing = 0;
		};
/* End PBXSourcesBuildPhase section */

/* Begin XCBuildConfiguration section */
		A1B2C3D4E5F6012345678913 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = dwarf;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				GCC_C_LANGUAGE_STANDARD = gnu17;
				GCC_NO_COMMON_BLOCKS = YES;
				GCC_OPTIMIZATION_LEVEL = 0;
				GCC_PREPROCESSOR_DEFINITIONS = (
					"DEBUG=1",
					"$(inherited)",
				);
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				SDKROOT = iphoneos;
				SWIFT_OPTIMIZATION_LEVEL = "-Onone";
			};
			name = Debug;
		};
		A1B2C3D4E5F6012345678914 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				ALWAYS_SEARCH_USER_PATHS = NO;
				CLANG_ENABLE_MODULES = YES;
				COPY_PHASE_STRIP = NO;
				DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";
				ENABLE_NS_ASSERTIONS = NO;
				ENABLE_STRICT_OBJC_MSGSEND = YES;
				GCC_C_LANGUAGE_STANDARD = gnu17;
				GCC_NO_COMMON_BLOCKS = YES;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				SDKROOT = iphoneos;
				SWIFT_COMPILATION_MODE = wholemodule;
			};
			name = Release;
		};
		A1B2C3D4E5F6012345678916 /* Debug */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_KEY_CFBundleDisplayName = RapidTrade;
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = "UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.example.RapidTrade;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SDKROOT = iphoneos;
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Debug;
		};
		A1B2C3D4E5F6012345678917 /* Release */ = {
			isa = XCBuildConfiguration;
			buildSettings = {
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = YES;
				INFOPLIST_KEY_CFBundleDisplayName = RapidTrade;
				INFOPLIST_KEY_UIApplicationSceneManifest_Generation = YES;
				INFOPLIST_KEY_UIApplicationSupportsIndirectInputEvents = YES;
				INFOPLIST_KEY_UILaunchScreen_Generation = YES;
				INFOPLIST_KEY_UISupportedInterfaceOrientations_iPhone = "UIInterfaceOrientationPortrait UIInterfaceOrientationLandscapeLeft UIInterfaceOrientationLandscapeRight";
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.example.RapidTrade;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SDKROOT = iphoneos;
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
			};
			name = Release;
		};
/* End XCBuildConfiguration section */

/* Begin XCConfigurationList section */
		A1B2C3D4E5F6012345678912 /* Build configuration list for PBXProject "RapidTrade" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				A1B2C3D4E5F6012345678913 /* Debug */,
				A1B2C3D4E5F6012345678914 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
		A1B2C3D4E5F6012345678915 /* Build configuration list for PBXNativeTarget "RapidTrade" */ = {
			isa = XCConfigurationList;
			buildConfigurations = (
				A1B2C3D4E5F6012345678916 /* Debug */,
				A1B2C3D4E5F6012345678917 /* Release */,
			);
			defaultConfigurationIsVisible = 0;
			defaultConfigurationName = Release;
		};
/* End XCConfigurationList section */
	};
	rootObject = A1B2C3D4E5F6012345678901 /* Project object */;
}
PBXPROJ

cat > RapidTrade.xcodeproj/xcshareddata/xcschemes/RapidTrade.xcscheme <<'XCSCHEME'
<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1600"
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
               BlueprintIdentifier = "A1B2C3D4E5F6012345678907"
               BuildableName = "RapidTrade.app"
               BlueprintName = "RapidTrade"
               ReferencedContainer = "container:RapidTrade.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES">
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
            BlueprintIdentifier = "A1B2C3D4E5F6012345678907"
            BuildableName = "RapidTrade.app"
            BlueprintName = "RapidTrade"
            ReferencedContainer = "container:RapidTrade.xcodeproj">
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
            BlueprintIdentifier = "A1B2C3D4E5F6012345678907"
            BuildableName = "RapidTrade.app"
            BlueprintName = "RapidTrade"
            ReferencedContainer = "container:RapidTrade.xcodeproj">
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
XCSCHEME

xcodebuild -project RapidTrade.xcodeproj -scheme RapidTrade -destination 'generic/platform=iOS Simulator' build