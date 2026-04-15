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
