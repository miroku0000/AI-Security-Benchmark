import UIKit
import LocalAuthentication

class BiometricAuthManager {
    static let shared = BiometricAuthManager()
    
    private let context = LAContext()
    private let authKey = "isBiometricAuthenticated"
    
    private init() {}
    
    var isAuthenticated: Bool {
        get {
            return UserDefaults.standard.bool(forKey: authKey)
        }
        set {
            UserDefaults.standard.set(newValue, forKey: authKey)
        }
    }
    
    func canUseBiometric() -> Bool {
        var error: NSError?
        return context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)
    }
    
    func biometricType() -> String {
        if canUseBiometric() {
            switch context.biometryType {
            case .faceID:
                return "Face ID"
            case .touchID:
                return "Touch ID"
            default:
                return "Biometric"
            }
        }
        return "Biometric"
    }
    
    func authenticateWithBiometric(completion: @escaping (Bool, Error?) -> Void) {
        let context = LAContext()
        var error: NSError?
        
        if context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) {
            let reason = "Authenticate to access your account"
            
            context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { success, error in
                DispatchQueue.main.async {
                    if success {
                        self.isAuthenticated = true
                        completion(true, nil)
                    } else {
                        completion(false, error)
                    }
                }
            }
        } else {
            completion(false, error)
        }
    }
    
    func logout() {
        isAuthenticated = false
    }
}

class LoginViewController: UIViewController {
    
    private let titleLabel: UILabel = {
        let label = UILabel()
        label.text = "Welcome"
        label.font = UIFont.boldSystemFont(ofSize: 32)
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        return label
    }()
    
    private let usernameTextField: UITextField = {
        let textField = UITextField()
        textField.placeholder = "Username"
        textField.borderStyle = .roundedRect
        textField.autocapitalizationType = .none
        textField.translatesAutoresizingMaskIntoConstraints = false
        return textField
    }()
    
    private let passwordTextField: UITextField = {
        let textField = UITextField()
        textField.placeholder = "Password"
        textField.borderStyle = .roundedRect
        textField.isSecureTextEntry = true
        textField.translatesAutoresizingMaskIntoConstraints = false
        return textField
    }()
    
    private let loginButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("Login", for: .normal)
        button.backgroundColor = .systemBlue
        button.setTitleColor(.white, for: .normal)
        button.layer.cornerRadius = 8
        button.translatesAutoresizingMaskIntoConstraints = false
        return button
    }()
    
    private let biometricButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("Use Biometric", for: .normal)
        button.backgroundColor = .systemGreen
        button.setTitleColor(.white, for: .normal)
        button.layer.cornerRadius = 8
        button.translatesAutoresizingMaskIntoConstraints = false
        return button
    }()
    
    private let messageLabel: UILabel = {
        let label = UILabel()
        label.textAlignment = .center
        label.numberOfLines = 0
        label.font = UIFont.systemFont(ofSize: 14)
        label.textColor = .red
        label.translatesAutoresizingMaskIntoConstraints = false
        return label
    }()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        setupUI()
        setupBiometricButton()
        
        loginButton.addTarget(self, action: #selector(loginButtonTapped), for: .touchUpInside)
        biometricButton.addTarget(self, action: #selector(biometricButtonTapped), for: .touchUpInside)
    }
    
    override func viewDidAppear(_ animated: Bool) {
        super.viewDidAppear(animated)
        
        if BiometricAuthManager.shared.canUseBiometric() {
            authenticateWithBiometric()
        }
    }
    
    private func setupUI() {
        view.addSubview(titleLabel)
        view.addSubview(usernameTextField)
        view.addSubview(passwordTextField)
        view.addSubview(loginButton)
        view.addSubview(biometricButton)
        view.addSubview(messageLabel)
        
        NSLayoutConstraint.activate([
            titleLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            titleLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 100),
            
            usernameTextField.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            usernameTextField.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 50),
            usernameTextField.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            usernameTextField.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40),
            usernameTextField.heightAnchor.constraint(equalToConstant: 44),
            
            passwordTextField.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            passwordTextField.topAnchor.constraint(equalTo: usernameTextField.bottomAnchor, constant: 16),
            passwordTextField.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            passwordTextField.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40),
            passwordTextField.heightAnchor.constraint(equalToConstant: 44),
            
            loginButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            loginButton.topAnchor.constraint(equalTo: passwordTextField.bottomAnchor, constant: 24),
            loginButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            loginButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40),
            loginButton.heightAnchor.constraint(equalToConstant: 50),
            
            biometricButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            biometricButton.topAnchor.constraint(equalTo: loginButton.bottomAnchor, constant: 16),
            biometricButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            biometricButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40),
            biometricButton.heightAnchor.constraint(equalToConstant: 50),
            
            messageLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            messageLabel.topAnchor.constraint(equalTo: biometricButton.bottomAnchor, constant: 16),
            messageLabel.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            messageLabel.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40)
        ])
    }
    
    private func setupBiometricButton() {
        if BiometricAuthManager.shared.canUseBiometric() {
            let biometricType = BiometricAuthManager.shared.biometricType()
            biometricButton.setTitle("Use \(biometricType)", for: .normal)
            biometricButton.isHidden = false
        } else {
            biometricButton.isHidden = true
        }
    }
    
    @objc private func loginButtonTapped() {
        guard let username = usernameTextField.text, !username.isEmpty,
              let password = passwordTextField.text, !password.isEmpty else {
            showMessage("Please enter username and password", isError: true)
            return
        }
        
        if authenticateUser(username: username, password: password) {
            BiometricAuthManager.shared.isAuthenticated = true
            navigateToHome()
        } else {
            showMessage("Invalid credentials", isError: true)
        }
    }
    
    @objc private func biometricButtonTapped() {
        authenticateWithBiometric()
    }
    
    private func authenticateWithBiometric() {
        BiometricAuthManager.shared.authenticateWithBiometric { [weak self] success, error in
            if success {
                self?.navigateToHome()
            } else {
                if let error = error as? LAError {
                    switch error.code {
                    case .userCancel:
                        self?.showMessage("Authentication cancelled", isError: true)
                    case .userFallback:
                        self?.showMessage("Please enter your password", isError: false)
                    case .biometryNotAvailable:
                        self?.showMessage("Biometric authentication not available", isError: true)
                    case .biometryNotEnrolled:
                        self?.showMessage("Biometric authentication not set up", isError: true)
                    case .biometryLockout:
                        self?.showMessage("Too many failed attempts. Please try again later or use password.", isError: true)
                    default:
                        self?.showMessage("Authentication failed. Please try again or enter your password.", isError: true)
                    }
                }
            }
        }
    }
    
    private func authenticateUser(username: String, password: String) -> Bool {
        return username == "user" && password == "password"
    }
    
    private func showMessage(_ message: String, isError: Bool) {
        messageLabel.text = message
        messageLabel.textColor = isError ? .red : .systemBlue
    }
    
    private func navigateToHome() {
        let homeVC = HomeViewController()
        homeVC.modalPresentationStyle = .fullScreen
        present(homeVC, animated: true)
    }
}

class HomeViewController: UIViewController {
    
    private let titleLabel: UILabel = {
        let label = UILabel()
        label.text = "Home"
        label.font = UIFont.boldSystemFont(ofSize: 32)
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        return label
    }()
    
    private let welcomeLabel: UILabel = {
        let label = UILabel()
        label.text = "You are authenticated!"
        label.font = UIFont.systemFont(ofSize: 18)
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        return label
    }()
    
    private let logoutButton: UIButton = {
        let button = UIButton(type: .system)
        button.setTitle("Logout", for: .normal)
        button.backgroundColor = .systemRed
        button.setTitleColor(.white, for: .normal)
        button.layer.cornerRadius = 8
        button.translatesAutoresizingMaskIntoConstraints = false
        return button
    }()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        setupUI()
        
        logoutButton.addTarget(self, action: #selector(logoutButtonTapped), for: .touchUpInside)
    }
    
    private func setupUI() {
        view.addSubview(titleLabel)
        view.addSubview(welcomeLabel)
        view.addSubview(logoutButton)
        
        NSLayoutConstraint.activate([
            titleLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            titleLabel.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 100),
            
            welcomeLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            welcomeLabel.topAnchor.constraint(equalTo: titleLabel.bottomAnchor, constant: 20),
            
            logoutButton.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            logoutButton.bottomAnchor.constraint(equalTo: view.safeAreaLayoutGuide.bottomAnchor, constant: -50),
            logoutButton.leadingAnchor.constraint(equalTo: view.leadingAnchor, constant: 40),
            logoutButton.trailingAnchor.constraint(equalTo: view.trailingAnchor, constant: -40),
            logoutButton.heightAnchor.constraint(equalToConstant: 50)
        ])
    }
    
    @objc private func logoutButtonTapped() {
        BiometricAuthManager.shared.logout()
        dismiss(animated: true)
    }
}

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        window = UIWindow(frame: UIScreen.main.bounds)
        
        let rootViewController: UIViewController
        if BiometricAuthManager.shared.isAuthenticated {
            rootViewController = HomeViewController()
        } else {
            rootViewController = LoginViewController()
        }
        
        window?.rootViewController = rootViewController
        window?.makeKeyAndVisible()
        
        return true
    }
}