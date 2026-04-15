import UIKit
import CommonCrypto
import Security

// MARK: - Password Hashing Utility

struct PasswordRecord: Codable {
    let salt: Data
    let hash: Data
}

class PasswordStorage {
    static let shared = PasswordStorage()
    private let storageKey = "com.example.OfflinePasswordStorage.passwordRecord"

    private init() {}

    func savePassword(_ password: String) -> Bool {
        guard let salt = generateSalt(length: 16) else { return false }
        guard let hash = sha256(password: password, salt: salt) else { return false }

        let record = PasswordRecord(salt: salt, hash: hash)
        do {
            let data = try JSONEncoder().encode(record)
            UserDefaults.standard.set(data, forKey: storageKey)
            return true
        } catch {
            return false
        }
    }

    func verifyPassword(_ password: String) -> Bool {
        guard let data = UserDefaults.standard.data(forKey: storageKey) else { return false }
        guard let record = try? JSONDecoder().decode(PasswordRecord.self, from: data) else { return false }
        guard let candidateHash = sha256(password: password, salt: record.salt) else { return false }
        return constantTimeCompare(lhs: record.hash, rhs: candidateHash)
    }

    private func generateSalt(length: Int) -> Data? {
        var data = Data(count: length)
        let result = data.withUnsafeMutableBytes { mutableBytes in
            SecRandomCopyBytes(kSecRandomDefault, length, mutableBytes.baseAddress!)
        }
        if result == errSecSuccess {
            return data
        } else {
            return nil
        }
    }

    private func sha256(password: String, salt: Data) -> Data? {
        guard let passwordData = password.data(using: .utf8) else { return nil }

        var combined = Data()
        combined.append(salt)
        combined.append(passwordData)

        var hash = Data(count: Int(CC_SHA256_DIGEST_LENGTH))
        _ = combined.withUnsafeBytes { combinedBytes in
            hash.withUnsafeMutableBytes { hashBytes in
                CC_SHA256(combinedBytes.baseAddress, CC_LONG(combined.count), hashBytes.bindMemory(to: UInt8.self).baseAddress)
            }
        }
        return hash
    }

    private func constantTimeCompare(lhs: Data, rhs: Data) -> Bool {
        guard lhs.count == rhs.count else { return false }
        var diff: UInt8 = 0
        for i in 0..<lhs.count {
            diff |= lhs[i] ^ rhs[i]
        }
        return diff == 0
    }
}

// MARK: - Simple UI

class ViewController: UIViewController {

    private let statusLabel: UILabel = {
        let label = UILabel()
        label.textAlignment = .center
        label.text = "Enter a password to save or verify."
        label.numberOfLines = 0
        label.translatesAutoresizingMaskIntoConstraints = false
        return label
    }()

    private let passwordField: UITextField = {
        let field = UITextField()
        field.placeholder = "Password"
        field.isSecureTextEntry = true
        field.borderStyle = .roundedRect
        field.translatesAutoresizingMaskIntoConstraints = false
        return field
    }()

    private let saveButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("Save Password", for: .normal)
        button.translatesAutoresizingMaskIntoConstraints = false
        return button
    }()

    private let verifyButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("Verify Password", for: .normal)
        button.translatesAutoresizingMaskIntoConstraints = false
        return button
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .white
        layoutUI()
        saveButton.addTarget(self, action: #selector(savePassword), for: .touchUpInside)
        verifyButton.addTarget(self, action: #selector(verifyPassword), for: .touchUpInside)
    }

    private func layoutUI() {
        view.addSubview(statusLabel)
        view.addSubview(passwordField)
        view.addSubview(saveButton)
        view.addSubview(verifyButton)

        let guide = view.safeAreaLayoutGuide

        NSLayoutConstraint.activate([
            statusLabel.topAnchor.constraint(equalTo: guide.topAnchor, constant: 40),
            statusLabel.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 20),
            statusLabel.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -20),

            passwordField.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 30),
            passwordField.leadingAnchor.constraint(equalTo: guide.leadingAnchor, constant: 20),
            passwordField.trailingAnchor.constraint(equalTo: guide.trailingAnchor, constant: -20),
            passwordField.heightAnchor.constraint(equalToConstant: 40),

            saveButton.topAnchor.constraint(equalTo: passwordField.bottomAnchor, constant: 20),
            saveButton.centerXAnchor.constraint(equalTo: guide.centerXAnchor),

            verifyButton.topAnchor.constraint(equalTo: saveButton.bottomAnchor, constant: 12),
            verifyButton.centerXAnchor.constraint(equalTo: guide.centerXAnchor),
        ])
    }

    @objc private func savePassword() {
        guard let password = passwordField.text, !password.isEmpty else {
            updateStatus("Please enter a password to save.", isError: true)
            return
        }

        let success = PasswordStorage.shared.savePassword(password)
        if success {
            updateStatus("Password saved securely (hashed + salted).", isError: false)
            passwordField.text = nil
        } else {
            updateStatus("Failed to save password.", isError: true)
        }
    }

    @objc private func verifyPassword() {
        guard let password = passwordField.text, !password.isEmpty else {
            updateStatus("Please enter a password to verify.", isError: true)
            return
        }

        let isValid = PasswordStorage.shared.verifyPassword(password)
        if isValid {
            updateStatus("Password verified successfully (offline).", isError: false)
        } else {
            updateStatus("Password verification failed.", isError: true)
        }
    }

    private func updateStatus(_ message: String, isError: Bool) {
        statusLabel.text = message
        statusLabel.textColor = isError ? .systemRed : .systemGreen
    }
}

// MARK: - App Delegate (iOS 10+ Compatible)

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    // For iOS 10–12 and also works on iOS 13+ when SceneDelegate is not used
    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {

        window = UIWindow(frame: UIScreen.main.bounds)
        let rootVC = ViewController()
        let navController = UINavigationController(rootViewController: rootVC)
        rootVC.title = "Offline Password Storage"
        window?.rootViewController = navController
        window?.makeKeyAndVisible()

        return true
    }
}