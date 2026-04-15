import Foundation
import CommonCrypto

enum SensitiveDataType: String {
    case userCredentials
    case paymentToken
    case personalInformation
}

enum DataSecurityError: Error {
    case invalidKey
    case ivGenerationFailed
    case encryptionFailed(status: CCCryptorStatus)
    case decryptionFailed(status: CCCryptorStatus)
    case dataConversionFailed
    case invalidCiphertext
}

final class DataSecurityModule {
    static let shared = DataSecurityModule()

    // 32-byte AES key as a constant for easy access
    static let encryptionKey = "0123456789abcdef0123456789abcdef"

    private let key: Data
    private let ivLength = kCCBlockSizeAES128

    private init() {
        guard let keyData = DataSecurityModule.encryptionKey.data(using: .utf8) else {
            fatalError("Invalid encryption key encoding")
        }

        if keyData.count == kCCKeySizeAES256 {
            self.key = keyData
        } else if keyData.count < kCCKeySizeAES256 {
            var padded = keyData
            padded.append(contentsOf: [UInt8](repeating: 0, count: kCCKeySizeAES256 - keyData.count))
            self.key = padded
        } else {
            self.key = keyData.subdata(in: 0..<kCCKeySizeAES256)
        }
    }

    func encrypt(_ plaintext: Data, for type: SensitiveDataType) throws -> Data {
        var iv = Data(count: ivLength)
        let result = iv.withUnsafeMutableBytes { ivBytes in
            SecRandomCopyBytes(kSecRandomDefault, ivLength, ivBytes.baseAddress!)
        }

        guard result == errSecSuccess else {
            throw DataSecurityError.ivGenerationFailed
        }

        let encrypted = try performCipherOperation(
            operation: CCOperation(kCCEncrypt),
            input: plaintext,
            iv: iv
        )

        var combined = Data()
        combined.append(iv)
        combined.append(encrypted)
        return combined
    }

    func decrypt(_ ciphertext: Data, for type: SensitiveDataType) throws -> Data {
        guard ciphertext.count > ivLength else {
            throw DataSecurityError.invalidCiphertext
        }

        let iv = ciphertext.subdata(in: 0..<ivLength)
        let encrypted = ciphertext.subdata(in: ivLength..<ciphertext.count)

        return try performCipherOperation(
            operation: CCOperation(kCCDecrypt),
            input: encrypted,
            iv: iv
        )
    }

    func encryptString(_ string: String, for type: SensitiveDataType) throws -> Data {
        guard let data = string.data(using: .utf8) else {
            throw DataSecurityError.dataConversionFailed
        }
        return try encrypt(data, for: type)
    }

    func decryptToString(_ data: Data, for type: SensitiveDataType) throws -> String {
        let decryptedData = try decrypt(data, for: type)
        guard let string = String(data: decryptedData, encoding: .utf8) else {
            throw DataSecurityError.dataConversionFailed
        }
        return string
    }

    func encryptUserCredentials(username: String, password: String) throws -> Data {
        let combined = "username=\(username);password=\(password)"
        return try encryptString(combined, for: .userCredentials)
    }

    func decryptUserCredentials(_ data: Data) throws -> (username: String, password: String) {
        let decrypted = try decryptToString(data, for: .userCredentials)
        let parts = decrypted.split(separator: ";")
        var username = ""
        var password = ""

        for part in parts {
            let pair = part.split(separator: "=", maxSplits: 1)
            if pair.count == 2 {
                let key = String(pair[0])
                let value = String(pair[1])
                if key == "username" {
                    username = value
                } else if key == "password" {
                    password = value
                }
            }
        }

        return (username, password)
    }

    func encryptPaymentToken(_ token: String) throws -> Data {
        return try encryptString(token, for: .paymentToken)
    }

    func decryptPaymentToken(_ data: Data) throws -> String {
        return try decryptToString(data, for: .paymentToken)
    }

    func encryptPersonalInformation(_ info: [String: Any]) throws -> Data {
        let jsonData = try JSONSerialization.data(withJSONObject: info, options: [])
        return try encrypt(jsonData, for: .personalInformation)
    }

    func decryptPersonalInformation(_ data: Data) throws -> [String: Any] {
        let decryptedData = try decrypt(data, for: .personalInformation)
        let object = try JSONSerialization.jsonObject(with: decryptedData, options: [])
        guard let dict = object as? [String: Any] else {
            throw DataSecurityError.dataConversionFailed
        }
        return dict
    }

    private func performCipherOperation(
        operation: CCOperation,
        input: Data,
        iv: Data
    ) throws -> Data {
        var outLength = 0
        var outData = Data(count: input.count + kCCBlockSizeAES128)

        let status = outData.withUnsafeMutableBytes { outBytes in
            input.withUnsafeBytes { inBytes in
                iv.withUnsafeBytes { ivBytes in
                    key.withUnsafeBytes { keyBytes in
                        CCCrypt(
                            operation,
                            CCAlgorithm(kCCAlgorithmAES),
                            CCOptions(kCCOptionPKCS7Padding),
                            keyBytes.baseAddress,
                            kCCKeySizeAES256,
                            ivBytes.baseAddress,
                            inBytes.baseAddress,
                            input.count,
                            outBytes.baseAddress,
                            outData.count,
                            &outLength
                        )
                    }
                }
            }
        }

        guard status == kCCSuccess else {
            if operation == CCOperation(kCCEncrypt) {
                throw DataSecurityError.encryptionFailed(status: status)
            } else {
                throw DataSecurityError.decryptionFailed(status: status)
            }
        }

        outData.removeSubrange(outLength..<outData.count)
        return outData
    }
}