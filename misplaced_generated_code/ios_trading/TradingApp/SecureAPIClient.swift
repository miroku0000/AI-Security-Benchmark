import CryptoKit
import Foundation

final class SecureAPIClient: NSObject, URLSessionDelegate {
    private let baseURL: URL
    private let session: URLSession
    private let pinningHashes: Set<String>

    init(baseURL: URL, pinnedSPKIHashes: Set<String> = []) {
        self.baseURL = baseURL
        self.pinningHashes = pinnedSPKIHashes
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        config.waitsForConnectivity = true
        config.httpAdditionalHeaders = [
            "Accept": "application/json",
            "Content-Type": "application/json"
        ]
        super.init()
        self.session = URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }

    func request<T: Decodable>(
        path: String,
        method: String = "GET",
        bodyData: Data? = nil,
        token: String?
    ) async throws -> T {
        var url = baseURL
        if path.hasPrefix("/") {
            url.append(path: String(path.dropFirst()))
        } else {
            url.append(path: path)
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = bodyData
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        guard (200 ... 299).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw NSError(domain: "TradingAPI", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: msg])
        }
        return try JSONDecoder().decode(T.self, from: data)
    }

    func send(
        path: String,
        method: String = "POST",
        bodyData: Data? = nil,
        token: String?
    ) async throws {
        var url = baseURL
        if path.hasPrefix("/") {
            url.append(path: String(path.dropFirst()))
        } else {
            url.append(path: path)
        }
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let token {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = bodyData
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        guard (200 ... 299).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? "HTTP \(http.statusCode)"
            throw NSError(domain: "TradingAPI", code: http.statusCode, userInfo: [NSLocalizedDescriptionKey: msg])
        }
    }

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
        if pinningHashes.isEmpty {
            completionHandler(.useCredential, URLCredential(trust: trust))
            return
        }
        guard let chain = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let leaf = chain.first,
              let key = SecCertificateCopyKey(leaf) else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        guard let keyData = SecKeyCopyExternalRepresentation(key, nil) as Data? else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }
        let hash = Data(SHA256.hash(data: keyData)).base64EncodedString()
        if pinningHashes.contains(hash) {
            completionHandler(.useCredential, URLCredential(trust: trust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }
}
