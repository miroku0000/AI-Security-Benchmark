import Foundation
import Security
import CryptoKit

enum KeychainError: Error {
    case unexpectedStatus(OSStatus)
}

enum SecureNetworking {
    static let service = "com.tradeplatform.auth"
    static let account = "accessToken"
}

final class KeychainTokenStore {
    func saveToken(_ data: Data) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: SecureNetworking.service,
            kSecAttrAccount as String: SecureNetworking.account
        ]
        SecItemDelete(query as CFDictionary)
        var attrs = query
        attrs[kSecValueData as String] = data
        attrs[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        let status = SecItemAdd(attrs as CFDictionary, nil)
        guard status == errSecSuccess else { throw KeychainError.unexpectedStatus(status) }
    }

    func readToken() throws -> Data? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: SecureNetworking.service,
            kSecAttrAccount as String: SecureNetworking.account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var out: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &out)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess else { throw KeychainError.unexpectedStatus(status) }
        return out as? Data
    }

    func deleteToken() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: SecureNetworking.service,
            kSecAttrAccount as String: SecureNetworking.account
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.unexpectedStatus(status)
        }
    }
}

final class PinningDelegate: NSObject, URLSessionDelegate, URLSessionTaskDelegate {
    private let pinnedSPKIHashes: Set<String>

    init(pinnedSPKIHashes: Set<String> = []) {
        self.pinnedSPKIHashes = pinnedSPKIHashes
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
        if pinnedSPKIHashes.isEmpty {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
            return
        }
        if let spki = Self.spkiSHA256(of: serverTrust), pinnedSPKIHashes.contains(spki) {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
        } else {
            completionHandler(.cancelAuthenticationChallenge, nil)
        }
    }

    private static func spkiSHA256(of trust: SecTrust) -> String? {
        guard let chain = SecTrustCopyCertificateChain(trust) as? [SecCertificate],
              let cert = chain.first else { return nil }
        return spkiHash(for: cert)
    }

    private static func spkiHash(for certificate: SecCertificate) -> String? {
        guard let key = SecCertificateCopyKey(certificate) else { return nil }
        var error: Unmanaged<CFError>?
        guard let keyData = SecKeyCopyExternalRepresentation(key, &error) as Data? else { return nil }
        return SHA256.hash(data: keyData).map { String(format: "%02x", $0) }.joined()
    }
}

final class SecureURLSessionFactory {
    static func makeSession(pinHashes: Set<String> = []) -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.tlsMinimumSupportedProtocolVersion = .TLSv12
        config.httpShouldSetCookies = false
        config.urlCache = nil
        config.requestCachePolicy = .reloadIgnoringLocalCacheData
        let delegate = PinningDelegate(pinnedSPKIHashes: pinHashes)
        return URLSession(configuration: config, delegate: delegate, delegateQueue: nil)
    }
}
