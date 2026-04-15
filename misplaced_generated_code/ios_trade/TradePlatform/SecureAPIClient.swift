import Foundation

actor SecureAPIClient {
    private let session: URLSession
    private let pinningDelegate: PinningDelegate?

    init() {
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        config.waitsForConnectivity = true
        config.httpAdditionalHeaders = [
            "Accept": "application/json",
            "Content-Type": "application/json"
        ]
        let delegate = PinningDelegate()
        self.pinningDelegate = delegate
        self.session = URLSession(configuration: config, delegate: delegate, delegateQueue: nil)
    }

    private func authorizedRequest(url: URL, method: String, body: Data? = nil) async throws -> (Data, HTTPURLResponse) {
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.httpBody = body
        if let tokenData = try? KeychainService.read(account: AppConfiguration.keychainTokenAccount),
           let token = String(data: tokenData, encoding: .utf8) {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        return (data, http)
    }

    func fetchPortfolio(base: URL) async throws -> PortfolioSnapshot {
        let url = base.appendingPathComponent("v1/portfolio")
        let (data, http) = try await authorizedRequest(url: url, method: "GET")
        guard (200...299).contains(http.statusCode) else {
            throw URLError(.cannotParseResponse)
        }
        let dec = JSONDecoder()
        dec.dateDecodingStrategy = .iso8601
        return try dec.decode(PortfolioSnapshot.self, from: data)
    }

    func submitOrder(base: URL, ticket: OrderTicket) async throws -> ExecutedOrder {
        let url = base.appendingPathComponent("v1/orders")
        let enc = JSONEncoder()
        enc.dateEncodingStrategy = .iso8601
        let body = try enc.encode(ticket)
        let (data, http) = try await authorizedRequest(url: url, method: "POST", body: body)
        guard (200...299).contains(http.statusCode) else {
            throw URLError(.cannotParseResponse)
        }
        return try JSONDecoder().decode(ExecutedOrder.self, from: data)
    }

    func login(base: URL, username: String, password: String) async throws -> String {
        struct LoginBody: Encodable { let username: String; let password: String }
        struct TokenResp: Decodable { let access_token: String }
        let url = base.appendingPathComponent("v1/auth/token")
        let body = try JSONEncoder().encode(LoginBody(username: username, password: password))
        let (data, http) = try await authorizedRequest(url: url, method: "POST", body: body)
        guard (200...299).contains(http.statusCode) else {
            throw URLError(.userAuthenticationRequired)
        }
        let t = try JSONDecoder().decode(TokenResp.self, from: data)
        return t.access_token
    }
}

final class PinningDelegate: NSObject, URLSessionDelegate, URLSessionTaskDelegate {
    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust else {
            completionHandler(.performDefaultHandling, nil)
            return
        }
        completionHandler(.useCredential, URLCredential(trust: trust))
    }
}
