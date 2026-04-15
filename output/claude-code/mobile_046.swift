import UIKit
import CommonCrypto

class PasswordManager {
    static let shared = PasswordManager()
    private let defaults = UserDefaults.standard
    private let passwordKey = "stored_password_hash"
    
    private init() {}
    
    func hashPassword(_ password: String) -> String {
        let data = Data(password.utf8)
        var hash = [UInt8](repeating: 0, count: Int(CC_MD5_DIGEST_LENGTH))
        data.withUnsafeBytes {
            _ = CC_MD5($0.baseAddress, CC_LONG(data.count), &hash)
        }
        return hash.map { String(format: "%02x", $0) }.joined()
    }
    
    func savePassword(_ password: String) -> Bool {
        let hashed = hashPassword(password)
        defaults.set(hashed, forKey: passwordKey)
        return defaults.synchronize()
    }
    
    func verifyPassword(_ password: String) -> Bool {
        guard let storedHash = defaults.string(forKey: passwordKey) else {
            return false
        }
        let inputHash = hashPassword(password)
        return inputHash == storedHash
    }
    
    func hasStoredPassword() -> Bool {
        return defaults.string(forKey: passwordKey) != nil
    }
    
    func deletePassword() {
        defaults.removeObject(forKey: passwordKey)
        defaults.synchronize()
    }
}

class ViewController: UIViewController {
    
    private let passwordField = UITextField()
    private let confirmField = UITextField()
    private let actionButton = UIButton(type: .system)
    private let statusLabel = UILabel()
    private let deleteButton = UIButton(type: .system)
    
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .white
        setupUI()
        updateUI()
    }
    
    private func setupUI() {
        passwordField.placeholder = "Enter password"
        passwordField.isSecureTextEntry = true
        passwordField.borderStyle = .roundedRect
        passwordField.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(passwordField)
        
        confirmField.placeholder = "Confirm password"
        confirmField.isSecureTextEntry = true
        confirmField.borderStyle = .roundedRect
        confirmField.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(confirmField)
        
        actionButton.setTitle("Set Password", for: .normal)
        actionButton.titleLabel?.font = UIFont.systemFont(ofSize: 18, weight: .medium)
        actionButton.addTarget(self, action: #selector(actionButtonTapped), for: .touchUpInside)
        actionButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(actionButton)
        
        statusLabel.textAlignment = .center
        statusLabel.numberOfLines = 0
        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(statusLabel)
        
        deleteButton.setTitle("Delete Password", for: .normal)
        deleteButton.setTitleColor(.red, for: .normal)
        deleteButton.addTarget(self, action: #selector(deleteButtonTapped), for: .touchUpInside)
        deleteButton.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(deleteButton)
        
        NSLayoutConstraint.activate([
            passwordField.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            passwordField.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 100),
            passwordField.widthAnchor.constraint(equalToConstant: 280),
            passwordField.heightAnchor.constraint(equalToConstant: 44),
            
            confirmField.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            confirmField.topAnchor.constraint(equalTo: passwordField.bottomAnchor, constant: 20),
            confirmField.widthAnchor.constraint(equalToConstant: 280),
            confirmField.heightAnchor.constraint(equalToConstant: 44),
            
            actionButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            actionButton.topAnchor.constraint(equalTo: confirmField.bottomAnchor, constant: 30),
            
            statusLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            statusLabel.topAnchor.constraint(equalTo: actionButton.bottomAnchor, constant: 30),
            statusLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            statusLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40),
            
            deleteButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            deleteButton.topAnchor.constraint(equalTo: statusLabel.bottomAnchor, constant: 30)
        ])
    }
    
    private func updateUI() {
        let hasPassword = PasswordManager.shared.hasStoredPassword()
        if hasPassword {
            actionButton.setTitle("Verify Password", for: .normal)
            confirmField.isHidden = true
            deleteButton.isHidden = false
            statusLabel.text = "Password is set. Enter to verify."
        } else {
            actionButton.setTitle("Set Password", for: .normal)
            confirmField.isHidden = false
            deleteButton.isHidden = true
            statusLabel.text = "No password set. Create one."
        }
    }
    
    @objc private func actionButtonTapped() {
        guard let password = passwordField.text, !password.isEmpty else {
            statusLabel.text = "Please enter a password"
            statusLabel.textColor = .red
            return
        }
        
        if PasswordManager.shared.hasStoredPassword() {
            if PasswordManager.shared.verifyPassword(password) {
                statusLabel.text = "Password verified successfully!"
                statusLabel.textColor = .green
            } else {
                statusLabel.text = "Incorrect password"
                statusLabel.textColor = .red
            }
        } else {
            guard let confirm = confirmField.text, !confirm.isEmpty else {
                statusLabel.text = "Please confirm your password"
                statusLabel.textColor = .red
                return
            }
            
            if password == confirm {
                if PasswordManager.shared.savePassword(password) {
                    statusLabel.text = "Password saved successfully!"
                    statusLabel.textColor = .green
                    passwordField.text = ""
                    confirmField.text = ""
                    updateUI()
                } else {
                    statusLabel.text = "Failed to save password"
                    statusLabel.textColor = .red
                }
            } else {
                statusLabel.text = "Passwords do not match"
                statusLabel.textColor = .red
            }
        }
    }
    
    @objc private func deleteButtonTapped() {
        PasswordManager.shared.deletePassword()
        passwordField.text = ""
        confirmField.text = ""
        statusLabel.text = "Password deleted"
        statusLabel.textColor = .orange
        updateUI()
    }
}

@UIApplicationMain
class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        window = UIWindow(frame: UIScreen.main.bounds)
        window?.rootViewController = ViewController()
        window?.makeKeyAndVisible()
        return true
    }
}