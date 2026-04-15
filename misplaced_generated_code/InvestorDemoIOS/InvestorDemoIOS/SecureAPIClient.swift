import Foundation
import Security
import CryptoKit

final class SecureAPIClient: NSObject {
    struct Environment {
        var baseURL: URL
        var authToken: String?
        var pinnedSPKIHashesBase64: Set<String>
        var timeout: TimeInterval
    }

    private let session: URLSession
    private var env: Environment
    private var pinnedDelegate: PinnedSessionDelegate?

    init(env: Environment) {
        self.env = env
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = env.timeout
        cfg.timeoutIntervalForResource = env.timeout
        cfg.waitsForConnectivity = true
        let del = PinnedSessionDelegate(pinnedSPKIHashesBase64: env.pinnedSPKIHashesBase64)
        self.pinnedDelegate = del
        self.session = URLSession(configuration: cfg, delegate: del, delegateQueue: nil)
        super.init()
    }

    func updateEnvironment(_ env: Environment) {
        self.env = env
        self.pinnedDelegate = PinnedSessionDelegate(pinnedSPKIHashesBase64: env.pinnedSPKIHashesBase64)
    }

    func get<T: Decodable>(_ path: String, completion: @escaping (Result<T, Error>) -> Void) {
        request(path: path, method: "GET", body: nil, completion: completion)
    }

    func post<T: Decodable, U: Encodable>(_ path: String, body: U, completion: @escaping (Result<T, Error>) -> Void) {
        do {
            let data = try JSONEncoder.trading.encode(body)
            request(path: path, method: "POST", body: data, completion: completion)
        } catch {
            completion(.failure(error))
        }
    }

    private func request<T: Decodable>(path: String, method: String, body: Data?, completion: @escaping (Result<T, Error>) -> Void) {
        var url = env.baseURL
        if path.hasPrefix("/") {
            url = url.appendingPathComponent(String(path.dropFirst()))
        } else {
            url = url.appendingPathComponent(path)
        }

        var req = URLRequest(url: url)
        req.httpMethod = method
        req.httpBody = body
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if body != nil {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token = env.authToken, !token.isEmpty {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let task = session.dataTask(with: req) { data, resp, err in
            if let err = err {
                completion(.failure(TradingError.network(err.localizedDescription)))
                return
            }
            guard let http = resp as? HTTPURLResponse else {
                completion(.failure(TradingError.network("Invalid response.")))
                return
            }
            guard (200...299).contains(http.statusCode) else {
                let msg: String
                if let data = data, let s = String(data: data, encoding: .utf8), !s.isEmpty {
                    msg = s
                } else {
                    msg = "HTTP \(http.statusCode)."
                }
                completion(.failure(TradingError.network(msg)))
                return
            }
            let payload = data ?? Data()
            do {
                let decoded = try JSONDecoder.trading.decode(T.self, from: payload)
                completion(.success(decoded))
            } catch {
                completion(.failure(error))
            }
        }
        task.resume()
    }
}

extension JSONEncoder {
    static let trading: JSONEncoder = {
        let e = JSONEncoder()
        e.dateEncodingStrategy = .iso8601
        return e
    }()
}

extension JSONDecoder {
    static let trading: JSONDecoder = {
        let d = JSONDecoder()
        d.dateDecodingStrategy = .iso8601
        return d
    }()
}

final class PinnedSessionDelegate: NSObject, URLSessionDelegate {
    private let pinnedSPKIHashesBase64: Set<String>

    init(pinnedSPKIHashesBase64: Set<String>) {
        self.pinnedSPKIHashesBase64 = pinnedSPKIHashesBase64
        super.init()
    }

    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let trust = challenge.protectionSpace.serverTrust else {
            completionHandler(.performDefaultHandling, nil)
            return
        }

        if pinnedSPKIHashesBase64.isEmpty {
            completionHandler(.performDefaultHandling, nil)
            return
        }

        guard SecTrustEvaluateWithError(trust, nil) else {
            completionHandler(.cancelAuthenticationChallenge, nil)
            return
        }

        let count = SecTrustGetCertificateCount(trust)
        for i in 0..<count {
            guard let cert = SecTrustGetCertificateAtIndex(trust, i),
                  let key = SecCertificateCopyKey(cert),
                  let keyData = SecKeyCopyExternalRepresentation(key, nil) as Data? else {
                continue
            }
            let hash = sha256Base64(keyData)
            if pinnedSPKIHashesBase64.contains(hash) {
                completionHandler(.useCredential, URLCredential(trust: trust))
                return
            }
        }
        completionHandler(.cancelAuthenticationChallenge, nil)
    }
}

private func sha256Base64(_ data: Data) -> String {
    let digest = SHA256.hash(data: data)
    return Data(digest).base64EncodedString()
}
