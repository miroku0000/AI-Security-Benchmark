import Foundation
import Combine

@MainActor
final class TradingAPIClient {
    private let baseURL: URL
    private let session: URLSession
    private let keychain: KeychainTokenStore
    private let jsonDecoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
    private let jsonEncoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
    private let tokenEncoder: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
    private let tokenDecoder: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()

    init(
        baseURL: URL = URL(string: "https://api.example-broker.com/v1")!,
        session: URLSession = SecureURLSessionFactory.makeSession(),
        keychain: KeychainTokenStore = KeychainTokenStore()
    ) {
        self.baseURL = baseURL
        self.session = session
        self.keychain = keychain
    }

    func setAccessToken(_ token: String) throws {
        let session = AuthSession(accessToken: token, expiresAt: Date().addingTimeInterval(3600))
        let data = try tokenEncoder.encode(session)
        try keychain.saveToken(data)
    }

    func clearAccessToken() throws {
        try keychain.deleteToken()
    }

    private func authorizedRequest(path: String, method: String, body: Data? = nil) async throws -> (Data, HTTPURLResponse) {
        guard let tokenData = try keychain.readToken(),
              let sessionAuth = try? tokenDecoder.decode(AuthSession.self, from: tokenData),
              sessionAuth.expiresAt > Date() else {
            throw URLError(.userAuthenticationRequired)
        }
        var req = URLRequest(url: baseURL.appendingPathComponent(path))
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("Bearer \(sessionAuth.accessToken)", forHTTPHeaderField: "Authorization")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = body
        }
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else { throw URLError(.badServerResponse) }
        return (data, http)
    }

    func fetchPortfolio() async throws -> PortfolioSnapshot {
        let (data, http) = try await authorizedRequest(path: "portfolio", method: "GET")
        guard (200...299).contains(http.statusCode) else {
            throw try decodeError(data)
        }
        return try jsonDecoder.decode(PortfolioSnapshot.self, from: data)
    }

    func placeOrder(_ request: PlaceOrderRequest) async throws -> PlaceOrderResponse {
        let body = try jsonEncoder.encode(request)
        let (data, http) = try await authorizedRequest(path: "orders", method: "POST", body: body)
        guard (200...299).contains(http.statusCode) else {
            throw try decodeError(data)
        }
        return try jsonDecoder.decode(PlaceOrderResponse.self, from: data)
    }

    private func decodeError(_ data: Data) throws -> Error {
        if let env = try? jsonDecoder.decode(APIErrorEnvelope.self, from: data) {
            return NSError(domain: "TradeAPI", code: 1, userInfo: [NSLocalizedDescriptionKey: "\(env.code): \(env.message)"])
        }
        return URLError(.badServerResponse)
    }
}

@MainActor
final class QuoteStreamService: ObservableObject {
    @Published private(set) var quotes: [String: StockQuote] = [:]
    @Published private(set) var isConnected = false
    @Published var lastError: String?

    private var webSocketTask: URLSessionWebSocketTask?
    private var session: URLSession?
    private var mockTask: Task<Void, Never>?

    func connectLive(url: URL? = nil) {
        disconnect()
        if let url {
            let cfg = URLSessionConfiguration.ephemeral
            cfg.tlsMinimumSupportedProtocolVersion = .TLSv12
            let sess = URLSession(configuration: cfg, delegate: PinningDelegate(pinnedSPKIHashes: []), delegateQueue: OperationQueue.main)
            session = sess
            let task = sess.webSocketTask(with: url)
            webSocketTask = task
            task.resume()
            isConnected = true
            receiveLoop()
        } else {
            startMockStream()
        }
    }

    func disconnect() {
        mockTask?.cancel()
        mockTask = nil
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        session?.invalidateAndCancel()
        session = nil
        isConnected = false
    }

    private func receiveLoop() {
        webSocketTask?.receive { [weak self] result in
            Task { @MainActor in
                guard let self else { return }
                switch result {
                case .failure(let err):
                    self.lastError = err.localizedDescription
                    self.isConnected = false
                case .success(let message):
                    switch message {
                    case .string(let text):
                        self.applyQuotePayload(text)
                    case .data(let data):
                        if let text = String(data: data, encoding: .utf8) {
                            self.applyQuotePayload(text)
                        }
                    @unknown default:
                        break
                    }
                    self.receiveLoop()
                }
            }
        }
    }

    private func applyQuotePayload(_ json: String) {
        guard let d = json.data(using: .utf8),
              let q = try? JSONDecoder().decode(StockQuote.self, from: d) else { return }
        quotes[q.symbol] = q
    }

    private func startMockStream() {
        isConnected = true
        let base: [String: (String, Decimal)] = [
            "AAPL": ("Apple Inc.", 178.5),
            "MSFT": ("Microsoft", 415.2),
            "GOOGL": ("Alphabet", 142.8),
            "AMZN": ("Amazon", 178.9),
            "NVDA": ("NVIDIA", 892.1),
            "META": ("Meta", 485.4),
            "TSLA": ("Tesla", 172.3),
            "JPM": ("JPMorgan", 195.6)
        ]
        mockTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled {
                for (sym, pair) in base {
                    try? await Task.sleep(nanoseconds: 120_000_000)
                    let jitter = Decimal(Double.random(in: -0.012...0.012))
                    let price = max(Decimal(0.01), pair.1 * (1 + jitter))
                    let spread = price * Decimal(0.0003)
                    let q = StockQuote(
                        symbol: sym,
                        name: pair.0,
                        last: price,
                        bid: price - spread,
                        ask: price + spread,
                        changePct: jitter * 100,
                        volume: Int64.random(in: 1_000_000...50_000_000),
                        timestamp: Date()
                    )
                    await MainActor.run {
                        self.quotes[sym] = q
                    }
                }
            }
        }
    }
}
