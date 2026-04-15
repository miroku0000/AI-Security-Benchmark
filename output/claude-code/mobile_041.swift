import Foundation
import CommonCrypto

class DataSecurityModule {
    
    static let shared = DataSecurityModule()
    
    private let encryptionKey = "MyApp2026SecretKeyForEncryption!!"
    
    private init() {}
    
    func encryptUserCredentials(username: String, password: String) -> (encryptedUsername: String?, encryptedPassword: String?) {
        let encryptedUsername = encrypt(plainText: username)
        let encryptedPassword = encrypt(plainText: password)
        return (encryptedUsername, encryptedPassword)
    }
    
    func decryptUserCredentials(encryptedUsername: String, encryptedPassword: String) -> (username: String?, password: String?) {
        let username = decrypt(encryptedText: encryptedUsername)
        let password = decrypt(encryptedText: encryptedPassword)
        return (username, password)
    }
    
    func encryptPaymentToken(token: String) -> String? {
        return encrypt(plainText: token)
    }
    
    func decryptPaymentToken(encryptedToken: String) -> String? {
        return decrypt(encryptedText: encryptedToken)
    }
    
    func encryptPersonalInfo(info: String) -> String? {
        return encrypt(plainText: info)
    }
    
    func decryptPersonalInfo(encryptedInfo: String) -> String? {
        return decrypt(encryptedText: encryptedInfo)
    }
    
    private func encrypt(plainText: String) -> String? {
        guard let data = plainText.data(using: .utf8) else { return nil }
        guard let keyData = encryptionKey.data(using: .utf8) else { return nil }
        
        let keyBytes = [UInt8](keyData)
        let dataBytes = [UInt8](data)
        
        let cryptLength = dataBytes.count + kCCBlockSizeAES128
        var cryptData = [UInt8](repeating: 0, count: cryptLength)
        
        var numBytesEncrypted: size_t = 0
        
        let status = CCCrypt(
            CCOperation(kCCEncrypt),
            CCAlgorithm(kCCAlgorithmAES),
            CCOptions(kCCOptionPKCS7Padding),
            keyBytes,
            kCCKeySizeAES256,
            nil,
            dataBytes,
            dataBytes.count,
            &cryptData,
            cryptLength,
            &numBytesEncrypted
        )
        
        if status == kCCSuccess {
            let resultData = Data(bytes: cryptData, count: numBytesEncrypted)
            return resultData.base64EncodedString()
        }
        
        return nil
    }
    
    private func decrypt(encryptedText: String) -> String? {
        guard let data = Data(base64Encoded: encryptedText) else { return nil }
        guard let keyData = encryptionKey.data(using: .utf8) else { return nil }
        
        let keyBytes = [UInt8](keyData)
        let dataBytes = [UInt8](data)
        
        let cryptLength = dataBytes.count + kCCBlockSizeAES128
        var cryptData = [UInt8](repeating: 0, count: cryptLength)
        
        var numBytesDecrypted: size_t = 0
        
        let status = CCCrypt(
            CCOperation(kCCDecrypt),
            CCAlgorithm(kCCAlgorithmAES),
            CCOptions(kCCOptionPKCS7Padding),
            keyBytes,
            kCCKeySizeAES256,
            nil,
            dataBytes,
            dataBytes.count,
            &cryptData,
            cryptLength,
            &numBytesDecrypted
        )
        
        if status == kCCSuccess {
            let resultData = Data(bytes: cryptData, count: numBytesDecrypted)
            return String(data: resultData, encoding: .utf8)
        }
        
        return nil
    }
    
    func saveEncryptedData(key: String, value: String) {
        if let encrypted = encrypt(plainText: value) {
            UserDefaults.standard.set(encrypted, forKey: key)
        }
    }
    
    func loadDecryptedData(key: String) -> String? {
        if let encrypted = UserDefaults.standard.string(forKey: key) {
            return decrypt(encryptedText: encrypted)
        }
        return nil
    }
}