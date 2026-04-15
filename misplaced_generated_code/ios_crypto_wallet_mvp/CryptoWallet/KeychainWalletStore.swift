import Foundation
import Security

enum KeychainWalletStore {
    private static let service = "com.cryptowallet.mvp.wallet"
    private static let account = "ethereum.private"

    static func savePrivateKey(_ key32: Data) throws {
        guard key32.count == 32 else { throw WalletError.invalidPrivateKey }
        try deletePrivateKeyIfExists()
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: key32,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]
        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else { throw WalletError.keyStoreFailed }
    }

    static func loadPrivateKey() throws -> Data {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound { throw WalletError.keyNotFound }
        guard status == errSecSuccess, let data = item as? Data else { throw WalletError.keyLoadFailed }
        guard data.count == 32 else { throw WalletError.invalidPrivateKey }
        return data
    }

    static func deletePrivateKeyIfExists() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        let status = SecItemDelete(query as CFDictionary)
        if status == errSecSuccess || status == errSecItemNotFound { return }
        throw WalletError.keyDeleteFailed
    }

    static func hasKey() -> Bool {
        (try? loadPrivateKey()) != nil
    }
}
