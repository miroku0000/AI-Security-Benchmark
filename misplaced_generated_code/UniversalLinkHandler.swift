import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    
    var window: UIWindow?
    
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = (scene as? UIWindowScene) else { return }
        
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = UINavigationController(rootViewController: HomeViewController())
        window?.makeKeyAndVisible()
        
        if let userActivity = connectionOptions.userActivities.first {
            handleUniversalLink(userActivity)
        }
    }
    
    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        handleUniversalLink(userActivity)
    }
    
    private func handleUniversalLink(_ userActivity: NSUserActivity) {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else {
            return
        }
        
        let linkHandler = UniversalLinkHandler()
        linkHandler.handleURL(url) { [weak self] destination in
            switch destination {
            case .passwordReset(let token):
                self?.navigateToPasswordReset(with: token)
            case .none:
                break
            }
        }
    }
    
    private func navigateToPasswordReset(with token: String) {
        let passwordResetVC = PasswordResetViewController(token: token)
        let navController = UINavigationController(rootViewController: passwordResetVC)
        navController.modalPresentationStyle = .fullScreen
        
        if let rootViewController = window?.rootViewController {
            rootViewController.present(navController, animated: true)
        }
    }
}

enum LinkDestination {
    case passwordReset(token: String)
}

class UniversalLinkHandler {
    
    func handleURL(_ url: URL, completion: @escaping (LinkDestination?) -> Void) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            completion(nil)
            return
        }
        
        switch components.path {
        case "/reset-password":
            if let token = components.queryItems?.first(where: { $0.name == "token" })?.value,
               !token.isEmpty {
                completion(.passwordReset(token: token))
            } else {
                completion(nil)
            }
        default:
            completion(nil)
        }
    }
}

class PasswordResetViewController: UIViewController {
    
    private let token: String
    private let stackView = UIStackView()
    private let titleLabel = UILabel()
    private let instructionLabel = UILabel()
    private let newPasswordTextField = UITextField()
    private let confirmPasswordTextField = UITextField()
    private let resetButton = UIButton(type: .system)
    private let errorLabel = UILabel()
    private let activityIndicator = UIActivityIndicatorView(style: .medium)
    
    init(token: String) {
        self.token = token
        super.init(nibName: nil, bundle: nil)
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        validateToken()
    }
    
    private func setupUI() {
        view.backgroundColor = .systemBackground
        
        navigationItem.title = "Reset Password"
        navigationItem.leftBarButtonItem = UIBarButtonItem(
            barButtonSystemItem: .cancel,
            target: self,
            action: #selector(cancelTapped)
        )
        
        titleLabel.text = "Create New Password"
        titleLabel.font = .systemFont(ofSize: 24, weight: .semibold)
        titleLabel.textAlignment = .center
        
        instructionLabel.text = "Enter your new password below"
        instructionLabel.font = .systemFont(ofSize: 16)
        instructionLabel.textColor = .secondaryLabel
        instructionLabel.textAlignment = .center
        instructionLabel.numberOfLines = 0
        
        newPasswordTextField.placeholder = "New Password"
        newPasswordTextField.isSecureTextEntry = true
        newPasswordTextField.borderStyle = .roundedRect
        newPasswordTextField.autocapitalizationType = .none
        newPasswordTextField.textContentType = .newPassword
        
        confirmPasswordTextField.placeholder = "Confirm Password"
        confirmPasswordTextField.isSecureTextEntry = true
        confirmPasswordTextField.borderStyle = .roundedRect
        confirmPasswordTextField.autocapitalizationType = .none
        confirmPasswordTextField.textContentType = .newPassword
        
        resetButton.setTitle("Reset Password", for: .normal)
        resetButton.titleLabel?.font = .systemFont(ofSize: 18, weight: .medium)
        resetButton.backgroundColor = .systemBlue
        resetButton.setTitleColor(.white, for: .normal)
        resetButton.layer.cornerRadius = 8
        resetButton.addTarget(self, action: #selector(resetPasswordTapped), for: .touchUpInside)
        
        errorLabel.textColor = .systemRed
        errorLabel.font = .systemFont(ofSize: 14)
        errorLabel.textAlignment = .center
        errorLabel.numberOfLines = 0
        errorLabel.isHidden = true
        
        activityIndicator.hidesWhenStopped = true
        
        stackView.axis = .vertical
        stackView.spacing = 20
        stackView.translatesAutoresizingMaskIntoConstraints = false
        
        stackView.addArrangedSubview(titleLabel)
        stackView.addArrangedSubview(instructionLabel)
        stackView.addArrangedSubview(newPasswordTextField)
        stackView.addArrangedSubview(confirmPasswordTextField)
        stackView.addArrangedSubview(resetButton)
        stackView.addArrangedSubview(errorLabel)
        stackView.addArrangedSubview(activityIndicator)
        
        view.addSubview(stackView)
        
        NSLayoutConstraint.activate([
            stackView.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 30),
            stackView.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -30),
            stackView.centerYAnchor.constraint(equalTo: view.centerYAnchor, constant: -50),
            
            resetButton.heightAnchor.constraint(equalToConstant: 50),
            newPasswordTextField.heightAnchor.constraint(equalToConstant: 50),
            confirmPasswordTextField.heightAnchor.constraint(equalToConstant: 50)
        ])
    }
    
    private func validateToken() {
        activityIndicator.startAnimating()
        resetButton.isEnabled = false
        
        AccountRecoveryService.shared.validateResetToken(token) { [weak self] isValid, error in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()
                
                if isValid {
                    self?.resetButton.isEnabled = true
                } else {
                    self?.showError(error?.localizedDescription ?? "Invalid or expired reset token")
                    self?.resetButton.isEnabled = false
                }
            }
        }
    }
    
    @objc private func resetPasswordTapped() {
        guard let newPassword = newPasswordTextField.text,
              let confirmPassword = confirmPasswordTextField.text else {
            showError("Please fill in all fields")
            return
        }
        
        guard !newPassword.isEmpty, !confirmPassword.isEmpty else {
            showError("Password fields cannot be empty")
            return
        }
        
        guard newPassword == confirmPassword else {
            showError("Passwords do not match")
            return
        }
        
        guard newPassword.count >= 8 else {
            showError("Password must be at least 8 characters")
            return
        }
        
        activityIndicator.startAnimating()
        resetButton.isEnabled = false
        errorLabel.isHidden = true
        
        AccountRecoveryService.shared.resetPassword(token: token, newPassword: newPassword) { [weak self] success, error in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()
                
                if success {
                    self?.showSuccessAndDismiss()
                } else {
                    self?.resetButton.isEnabled = true
                    self?.showError(error?.localizedDescription ?? "Failed to reset password")
                }
            }
        }
    }
    
    private func showError(_ message: String) {
        errorLabel.text = message
        errorLabel.isHidden = false
    }
    
    private func showSuccessAndDismiss() {
        let alert = UIAlertController(
            title: "Success",
            message: "Your password has been reset successfully. Please log in with your new password.",
            preferredStyle: .alert
        )
        
        alert.addAction(UIAlertAction(title: "OK", style: .default) { [weak self] _ in
            self?.dismiss(animated: true) {
                NotificationCenter.default.post(name: .passwordResetCompleted, object: nil)
            }
        })
        
        present(alert, animated: true)
    }
    
    @objc private func cancelTapped() {
        dismiss(animated: true)
    }
}

class AccountRecoveryService {
    
    static let shared = AccountRecoveryService()
    private let baseURL = "https://myapp.com/api"
    
    private init() {}
    
    func validateResetToken(_ token: String, completion: @escaping (Bool, Error?) -> Void) {
        guard let url = URL(string: "\(baseURL)/validate-reset-token") else {
            completion(false, NSError(domain: "AccountRecovery", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid URL"]))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["token": token]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(false, error)
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(false, NSError(domain: "AccountRecovery", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"]))
                return
            }
            
            completion(httpResponse.statusCode == 200, nil)
        }.resume()
    }
    
    func resetPassword(token: String, newPassword: String, completion: @escaping (Bool, Error?) -> Void) {
        guard let url = URL(string: "\(baseURL)/reset-password") else {
            completion(false, NSError(domain: "AccountRecovery", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid URL"]))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = [
            "token": token,
            "newPassword": newPassword
        ]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(false, error)
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(false, NSError(domain: "AccountRecovery", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"]))
                return
            }
            
            if httpResponse.statusCode == 200 {
                completion(true, nil)
            } else {
                let errorMessage = self.parseErrorMessage(from: data) ?? "Password reset failed"
                completion(false, NSError(domain: "AccountRecovery", code: httpResponse.statusCode, userInfo: [NSLocalizedDescriptionKey: errorMessage]))
            }
        }.resume()
    }
    
    private func parseErrorMessage(from data: Data?) -> String? {
        guard let data = data,
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let message = json["message"] as? String else {
            return nil
        }
        return message
    }
}

extension Notification.Name {
    static let passwordResetCompleted = Notification.Name("passwordResetCompleted")
}

class HomeViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        title = "Home"
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(passwordResetCompleted),
            name: .passwordResetCompleted,
            object: nil
        )
    }
    
    @objc private func passwordResetCompleted() {
        // Handle navigation to login screen or refresh user state
    }
    
    deinit {
        NotificationCenter.default.removeObserver(self)
    }
}