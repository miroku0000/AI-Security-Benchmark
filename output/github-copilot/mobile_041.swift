import CommonCrypto
import Security

public struct UserCredentials: Codable, Equatable {
    public let username: String
    public let password: String

    public init(username: String, password: String) {
        self.username = username
        self.password = password
    }
}

public struct PaymentToken: Codable, Equatable {
    public let token: String
    public let provider: String
    public let lastFourDigits: String

    public init(token: String, provider: String, lastFourDigits: String) {
        self.token = token
        self.provider = provider
        self.lastFourDigits = lastFourDigits
    }
}

public struct PersonalInformation: Codable, Equatable {
    public let fullName: String
    public let email: String
    public let phoneNumber: String
    public let address: String

    public init(fullName: String, email: String, phoneNumber: String, address: String) {
        self.fullName = fullName
        self.email = email
        self.phoneNumber = phoneNumber
        self.address = address
    }
}

public enum LocalDataSecurityError: Error {
    case invalidCombinedData
    case invalidKeyLength
    case randomGenerationFailed(OSStatus)
    case encryptionFailed(CCCryptorStatus)
    case decryptionFailed(CCCryptorStatus)
    case keychainError(OSStatus)
}

public final class LocalDataSecurityModule {
    public static let encryptionKey = "com.example.initialrelease.localdata.aes256.key"

    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()
    private let service: String

    public init(service: String = Bundle.main.bundleIdentifier ?? "com.example.app") {
        self.service = service
    }

    public func encryptCredentials(_ credentials: UserCredentials) throws -> Data {
        try encrypt(credentials)
    }

    public func decryptCredentials(_ encryptedData: Data) throws -> UserCredentials {
        try decrypt(UserCredentials.self, from: encryptedData)
    }

    public func encryptPaymentToken(_ paymentToken: PaymentToken) throws -> Data {
        try encrypt(paymentToken)
    }

    public func decryptPaymentToken(_ encryptedData: Data) throws -> PaymentToken {
        try decrypt(PaymentToken.self, from: encryptedData)
    }

    public func encryptPersonalInformation(_ personalInformation: PersonalInformation) throws -> Data {
        try encrypt(personalInformation)
    }

    public func decryptPersonalInformation(_ encryptedData: Data) throws -> PersonalInformation {
        try decrypt(PersonalInformation.self, from: encryptedData)
    }

    public func encrypt<T: Encodable>(_ value: T) throws -> Data {
        let plaintext = try encoder.encode(value)
        let key = try fetchOrCreateKey()
        let iv = try randomData(count: kCCBlockSizeAES128)
        let ciphertext = try crypt(
            operation: CCOperation(kCCEncrypt),
            input: plaintext,
            key: key,
            iv: iv
        )

        var combined = Data()
        combined.append(iv)
        combined.append(ciphertext)
        return combined
    }

    public func decrypt<T: Decodable>(_ type: T.Type, from encryptedData: Data) throws -> T {
        guard encryptedData.count > kCCBlockSizeAES128 else {
            throw LocalDataSecurityError.invalidCombinedData
        }

        let iv = encryptedData.prefix(kCCBlockSizeAES128)
        let ciphertext = encryptedData.dropFirst(kCCBlockSizeAES128)
        let key = try fetchOrCreateKey()
        let plaintext = try crypt(
            operation: CCOperation(kCCDecrypt),
            input: Data(ciphertext),
            key: key,
            iv: Data(iv)
        )
        return try decoder.decode(T.self, from: plaintext)
    }

    private func fetchOrCreateKey() throws -> Data {
        if let existingKey = try readKeyFromKeychain() {
            return existingKey
        }

        let newKey = try randomData(count: kCCKeySizeAES256)
        try storeKeyInKeychain(newKey)
        return newKey
    }

    private func readKeyFromKeychain() throws -> Data? {
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: Self.encryptionKey,
            kSecReturnData: true,
            kSecMatchLimit: kSecMatchLimitOne
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        switch status {
        case errSecSuccess:
            guard let keyData = item as? Data else {
                throw LocalDataSecurityError.keychainError(errSecInternalComponent)
            }
            return keyData
        case errSecItemNotFound:
            return nil
        default:
            throw LocalDataSecurityError.keychainError(status)
        }
    }

    private func storeKeyInKeychain(_ key: Data) throws {
        let query: [CFString: Any] = [
            kSecClass: kSecClassGenericPassword,
            kSecAttrService: service,
            kSecAttrAccount: Self.encryptionKey,
            kSecValueData: key,
            kSecAttrAccessible: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let addStatus = SecItemAdd(query as CFDictionary, nil)
        if addStatus == errSecDuplicateItem {
            let updateQuery: [CFString: Any] = [
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: service,
                kSecAttrAccount: Self.encryptionKey
            ]
            let attributesToUpdate: [CFString: Any] = [
                kSecValueData: key
            ]
            let updateStatus = SecItemUpdate(updateQuery as CFDictionary, attributesToUpdate as CFDictionary)
            guard updateStatus == errSecSuccess else {
                throw LocalDataSecurityError.keychainError(updateStatus)
            }
            return
        }

        guard addStatus == errSecSuccess else {
            throw LocalDataSecurityError.keychainError(addStatus)
        }
    }

    private func randomData(count: Int) throws -> Data {
        var data = Data(count: count)
        let status = data.withUnsafeMutableBytes { buffer in
            SecRandomCopyBytes(kSecRandomDefault, count, buffer.baseAddress!)
        }

        guard status == errSecSuccess else {
            throw LocalDataSecurityError.randomGenerationFailed(status)
        }

        return data
    }

    private func crypt(operation: CCOperation, input: Data, key: Data, iv: Data) throws -> Data {
        guard key.count == kCCKeySizeAES256 else {
            throw LocalDataSecurityError.invalidKeyLength
        }

        var output = Data(count: input.count + kCCBlockSizeAES128)
        var outputLength = 0

        let status = output.withUnsafeMutableBytes { outputBytes in
            input.withUnsafeBytes { inputBytes in
                iv.withUnsafeBytes { ivBytes in
                    key.withUnsafeBytes { keyBytes in
                        CCCrypt(
                            operation,
                            CCAlgorithm(kCCAlgorithmAES),
                            CCOptions(kCCOptionPKCS7Padding),
                            keyBytes.baseAddress,
                            key.count,
                            ivBytes.baseAddress,
                            inputBytes.baseAddress,
                            input.count,
                            outputBytes.baseAddress,
                            output.count,
                            &outputLength
                        )
                    }
                }
            }
        }

        guard status == kCCSuccess else {
            if operation == CCOperation(kCCEncrypt) {
                throw LocalDataSecurityError.encryptionFailed(status)
            }
            throw LocalDataSecurityError.decryptionFailed(status)
        }

        output.removeSubrange(outputLength..<output.count)
        return output
    }
}