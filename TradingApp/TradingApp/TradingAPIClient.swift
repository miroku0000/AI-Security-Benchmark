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
