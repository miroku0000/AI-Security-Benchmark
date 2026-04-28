import UIKit
import Foundation
import Security
import CommonCrypto

enum PasswordStorageError: LocalizedError {
    case emptyUsername
    case emptyPassword
    case randomGenerationFailed(OSStatus)
    case keyDerivationFailed(Int32)
    case encodingFailed
    case decodingFailed
    case unexpectedKeychainStatus(OSStatus)

    var errorDescription: String? {
        switch self {
        case .emptyUsername:
            return "Username cannot be empty."
        case .emptyPassword:
            return "Password cannot be empty."
        case .randomGenerationFailed(let status):
            return "Failed to generate random salt (\(status))."
        case .keyDerivationFailed(let status):
            return "Failed to derive password hash (\(status))."
        case .encodingFailed:
            return "Failed to encode password record."
        case .decodingFailed:
            return "Failed to decode password record."
        case .unexpectedKeychainStatus(let status):
            return "Keychain operation failed (\(status))."
        }
    }
}

struct PasswordRecord: Codable {
    let version: Int
    let rounds: Int
    let keyLength: Int
    let salt: Data
    let hash: Data
}

enum PBKDF2Hasher {
    static let defaultRounds = 30000
    static let defaultSaltLength = 16
    static let defaultKeyLength = 32

    static func randomSalt(length: Int = defaultSaltLength) throws -> Data {
        var salt = Data(count: length)
        let status = salt.withUnsafeMutableBytes { buffer in
            SecRandomCopyBytes(kSecRandomDefault, length, buffer.baseAddress!)
        }
        guard status == errSecSuccess else {
            throw PasswordStorageError.randomGenerationFailed(status)
        }
        return salt
    }

    static func hash(
        password: String,
        salt: Data,
        rounds: Int = defaultRounds,
        keyLength: Int = defaultKeyLength
    ) throws -> Data {
        guard !password.isEmpty else {
            throw PasswordStorageError.emptyPassword
        }

        var derivedKey = Data(count: keyLength)
        let passwordLength = password.lengthOfBytes(using: .utf8)

        let status: Int32 = derivedKey.withUnsafeMutableBytes { derivedBuffer in
            salt.withUnsafeBytes { saltBuffer in
                password.withCString { passwordPointer in
                    CCKeyDerivationPBKDF(
                        CCPBKDFAlgorithm(kCCPBKDF2),
                        passwordPointer,
                        passwordLength,
                        saltBuffer.bindMemory(to: UInt8.self).baseAddress,
                        salt.count,
                        CCPseudoRandomAlgorithm(kCCPRFHmacAlgSHA256),
                        UInt32(rounds),
                        derivedBuffer.bindMemory(to: UInt8.self).baseAddress,
                        keyLength
                    )
                }
            }
        }

        guard status == kCCSuccess else {
            throw PasswordStorageError.keyDerivationFailed(status)
        }

        return derivedKey
    }

    static func verify(password: String, against expectedHash: Data, salt: Data, rounds: Int, keyLength: Int) throws -> Bool {
        let candidateHash = try hash(password: password, salt: salt, rounds: rounds, keyLength: keyLength)
        return constantTimeEquals(candidateHash, expectedHash)
    }

    static func constantTimeEquals(_ lhs: Data, _ rhs: Data) -> Bool {
        guard lhs.count == rhs.count else {
            return false
        }

        var difference: UInt8 = 0
        for index in 0..<lhs.count {
            difference |= lhs[index] ^ rhs[index]
        }
        return difference == 0
    }
}

final class PasswordStorage {
    static let shared = PasswordStorage()

    private let service = "com.example.offline-password-storage"
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    private init() {}

    func savePassword(_ password: String, for username: String) throws {
        let account = try normalizedAccountName(username)
        let salt = try PBKDF2Hasher.randomSalt()
        let hash = try PBKDF2Hasher.hash(password: password, salt: salt)

        let record = PasswordRecord(
            version: 1,
            rounds: PBKDF2Hasher.defaultRounds,
            keyLength: PBKDF2Hasher.defaultKeyLength,
            salt: salt,
            hash: hash
        )

        let encodedRecord = try encoded(record: record)
        let query = baseQuery(for: account)

        let status = SecItemCopyMatching(query as CFDictionary, nil)
        if status == errSecItemNotFound {
            var addQuery = query
            addQuery[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            addQuery[kSecValueData as String] = encodedRecord

            let addStatus = SecItemAdd(addQuery as CFDictionary, nil)
            guard addStatus == errSecSuccess else {
                throw PasswordStorageError.unexpectedKeychainStatus(addStatus)
            }
            return
        }

        guard status == errSecSuccess else {
            throw PasswordStorageError.unexpectedKeychainStatus(status)
        }

        let updateStatus = SecItemUpdate(
            query as CFDictionary,
            [kSecValueData as String: encodedRecord] as CFDictionary
        )
        guard updateStatus == errSecSuccess else {
            throw PasswordStorageError.unexpectedKeychainStatus(updateStatus)
        }
    }

    func verifyPassword(_ password: String, for username: String) throws -> Bool {
        let account = try normalizedAccountName(username)
        guard let record = try loadRecord(for: account) else {
            return false
        }

        return try PBKDF2Hasher.verify(
            password: password,
            against: record.hash,
            salt: record.salt,
            rounds: record.rounds,
            keyLength: record.keyLength
        )
    }

    func deletePassword(for username: String) throws {
        let account = try normalizedAccountName(username)
        let status = SecItemDelete(baseQuery(for: account) as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw PasswordStorageError.unexpectedKeychainStatus(status)
        }
    }

    private func loadRecord(for account: String) throws -> PasswordRecord? {
        var query = baseQuery(for: account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        if status == errSecItemNotFound {
            return nil
        }

        guard status == errSecSuccess else {
            throw PasswordStorageError.unexpectedKeychainStatus(status)
        }

        guard let data = result as? Data else {
            throw PasswordStorageError.decodingFailed
        }

        do {
            return try decoder.decode(PasswordRecord.self, from: data)
        } catch {
            throw PasswordStorageError.decodingFailed
        }
    }

    private func encoded(record: PasswordRecord) throws -> Data {
        do {
            return try encoder.encode(record)
        } catch {
            throw PasswordStorageError.encodingFailed
        }
    }

    private func normalizedAccountName(_ username: String) throws -> String {
        let account = username.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !account.isEmpty else {
            throw PasswordStorageError.emptyUsername
        }
        return account
    }

    private func baseQuery(for account: String) -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
    }
}

final class PasswordDemoViewController: UIViewController {
    private let usernameField = UITextField()
    private let passwordField = UITextField()
    private let statusLabel = UILabel()
    private let storeButton = UIButton(type: .system)
    private let verifyButton = UIButton(type: .system)
    private let deleteButton = UIButton(type: .system)

    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Offline Auth"
        configureView()
        configureFields()
        configureButtons()
        configureStatusLabel()
        layoutViews()
    }

    private func configureView() {
        if #available(iOS 13.0, *) {
            view.backgroundColor = .systemBackground
        } else {
            view.backgroundColor = .white
        }
    }

    private func configureFields() {
        usernameField.placeholder = "Username"
        usernameField.borderStyle = .roundedRect
        usernameField.autocapitalizationType = .none
        usernameField.autocorrectionType = .no
        usernameField.clearButtonMode = .whileEditing
        usernameField.textContentType = .username

        passwordField.placeholder = "Password"
        passwordField.borderStyle = .roundedRect
        passwordField.isSecureTextEntry = true
        passwordField.autocapitalizationType = .none
        passwordField.autocorrectionType = .no
        passwordField.clearButtonMode = .whileEditing
        if #available(iOS 11.0, *) {
            passwordField.textContentType = .password
        }
    }

    private func configureButtons() {
        storeButton.setTitle("Store Password", for: .normal)
        verifyButton.setTitle("Verify Offline", for: .normal)
        deleteButton.setTitle("Delete Stored Password", for: .normal)

        storeButton.addTarget(self, action: #selector(storePassword), for: .touchUpInside)
        verifyButton.addTarget(self, action: #selector(verifyPassword), for: .touchUpInside)
        deleteButton.addTarget(self, action: #selector(deletePassword), for: .touchUpInside)
    }

    private func configureStatusLabel() {
        statusLabel.numberOfLines = 0
        statusLabel.textAlignment = .center
        statusLabel.font = UIFont.systemFont(ofSize: 15)
        statusLabel.text = "Enter a username and password."
        if #available(iOS 13.0, *) {
            statusLabel.textColor = .label
        } else {
            statusLabel.textColor = .black
        }
    }

    private func layoutViews() {
        let stack = UIStackView(arrangedSubviews: [
            usernameField,
            passwordField,
            storeButton,
            verifyButton,
            deleteButton,
            statusLabel
        ])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(stack)

        let margins = view.layoutMarginsGuide
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: margins.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: margins.trailingAnchor)
        ])

        if #available(iOS 11.0, *) {
            NSLayoutConstraint.activate([
                stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 24)
            ])
        } else {
            NSLayoutConstraint.activate([
                stack.topAnchor.constraint(equalTo: topLayoutGuide.bottomAnchor, constant: 24)
            ])
        }
    }

    @objc private func storePassword() {
        do {
            try PasswordStorage.shared.savePassword(currentPassword(), for: currentUsername())
            setStatus("Password stored locally.", isError: false)
        } catch {
            setStatus(error.localizedDescription, isError: true)
        }
    }

    @objc private func verifyPassword() {
        do {
            let verified = try PasswordStorage.shared.verifyPassword(currentPassword(), for: currentUsername())
            setStatus(verified ? "Password verified offline." : "Password verification failed.", isError: !verified)
        } catch {
            setStatus(error.localizedDescription, isError: true)
        }
    }

    @objc private func deletePassword() {
        do {
            try PasswordStorage.shared.deletePassword(for: currentUsername())
            setStatus("Stored password deleted.", isError: false)
        } catch {
            setStatus(error.localizedDescription, isError: true)
        }
    }

    private func currentUsername() -> String {
        usernameField.text ?? ""
    }

    private func currentPassword() -> String {
        passwordField.text ?? ""
    }

    private func setStatus(_ message: String, isError: Bool) {
        statusLabel.text = message
        if #available(iOS 13.0, *) {
            statusLabel.textColor = isError ? .systemRed : .label
        } else {
            statusLabel.textColor = isError ? .red : .black
        }
    }
}

@UIApplicationMain
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        let rootViewController = UINavigationController(rootViewController: PasswordDemoViewController())
        window.rootViewController = rootViewController
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}