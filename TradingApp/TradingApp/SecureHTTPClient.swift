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
