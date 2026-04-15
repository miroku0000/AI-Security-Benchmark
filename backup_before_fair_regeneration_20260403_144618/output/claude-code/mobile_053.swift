import UIKit

// MARK: - Models

struct PromoCode: Codable {
    let code: String
    let discountPercentage: Int
    let isValid: Bool
    let expiresAt: String?
}

struct PromoValidationResponse: Codable {
    let success: Bool
    let promo: PromoCode?
    let message: String
}

// MARK: - PromoService

final class PromoService {
    static let shared = PromoService()
    private init() {}

    func validateAndApplyPromo(code: String, completion: @escaping (Result<PromoValidationResponse, Error>) -> Void) {
        guard let url = URL(string: "https://api.myapp.com/v1/promo/redeem") else {
            completion(.failure(PromoError.invalidURL))
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Send only the promo code. The server determines the actual discount.
        // Never trust client-supplied discount values.
        let body: [String: String] = ["code": code]

        do {
            request.httpBody = try JSONEncoder().encode(body)
        } catch {
            completion(.failure(error))
            return
        }

        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }

            guard let httpResponse = response as? HTTPURLResponse,
                  (200...299).contains(httpResponse.statusCode),
                  let data = data else {
                completion(.failure(PromoError.serverError))
                return
            }

            do {
                let result = try JSONDecoder().decode(PromoValidationResponse.self, from: data)
                completion(.success(result))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}

enum PromoError: LocalizedError {
    case invalidURL
    case serverError
    case invalidPromoLink
    case missingPromoCode

    var errorDescription: String? {
        switch self {
        case .invalidURL: return "Invalid service URL."
        case .serverError: return "Server error. Please try again."
        case .invalidPromoLink: return "This promo link is not valid."
        case .missingPromoCode: return "No promo code found in this link."
        }
    }
}

// MARK: - PromoDeepLinkHandler

final class PromoDeepLinkHandler {
    static let shared = PromoDeepLinkHandler()
    private init() {}

    private let allowedHosts = ["myapp.com", "www.myapp.com"]

    func handleUniversalLink(_ url: URL) -> String? {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true),
              let host = components.host,
              allowedHosts.contains(host),
              components.path == "/promo" else {
            return nil
        }

        guard let queryItems = components.queryItems,
              let code = queryItems.first(where: { $0.name == "code" })?.value,
              !code.isEmpty else {
            return nil
        }

        // Note: We intentionally ignore the "discount" URL parameter.
        // The server is the sole authority on what discount a promo code provides.
        // Trusting a client-supplied discount value would be a security vulnerability.

        return code
    }
}

// MARK: - PromoViewController

final class PromoViewController: UIViewController {
    private let activityIndicator = UIActivityIndicatorView(style: .large)
    private let statusLabel = UILabel()
    private let discountLabel = UILabel()
    private let iconImageView = UIImageView()

    private var promoCode: String?

    convenience init(promoCode: String) {
        self.init()
        self.promoCode = promoCode
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()

        if let code = promoCode {
            redeemPromo(code: code)
        }
    }

    private func setupUI() {
        view.backgroundColor = .systemBackground
        title = "Promo"

        iconImageView.translatesAutoresizingMaskIntoConstraints = false
        iconImageView.image = UIImage(systemName: "tag.fill")
        iconImageView.tintColor = .systemGreen
        iconImageView.contentMode = .scaleAspectFit

        statusLabel.translatesAutoresizingMaskIntoConstraints = false
        statusLabel.textAlignment = .center
        statusLabel.font = .preferredFont(forTextStyle: .headline)
        statusLabel.numberOfLines = 0
        statusLabel.text = "Applying promo code..."

        discountLabel.translatesAutoresizingMaskIntoConstraints = false
        discountLabel.textAlignment = .center
        discountLabel.font = .systemFont(ofSize: 48, weight: .bold)
        discountLabel.textColor = .systemGreen
        discountLabel.isHidden = true

        activityIndicator.translatesAutoresizingMaskIntoConstraints = false
        activityIndicator.startAnimating()

        let stack = UIStackView(arrangedSubviews: [iconImageView, discountLabel, statusLabel, activityIndicator])
        stack.axis = .vertical
        stack.spacing = 16
        stack.alignment = .center
        stack.translatesAutoresizingMaskIntoConstraints = false

        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            stack.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 32),
            stack.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -32),
            iconImageView.widthAnchor.constraint(equalToConstant: 64),
            iconImageView.heightAnchor.constraint(equalToConstant: 64),
        ])
    }

    private func redeemPromo(code: String) {
        PromoService.shared.validateAndApplyPromo(code: code) { [weak self] result in
            DispatchQueue.main.async {
                self?.activityIndicator.stopAnimating()

                switch result {
                case .success(let response):
                    if response.success, let promo = response.promo {
                        self?.showSuccess(discount: promo.discountPercentage)
                    } else {
                        self?.showError(message: response.message)
                    }
                case .failure(let error):
                    self?.showError(message: error.localizedDescription)
                }
            }
        }
    }

    private func showSuccess(discount: Int) {
        iconImageView.image = UIImage(systemName: "checkmark.seal.fill")
        iconImageView.tintColor = .systemGreen
        discountLabel.text = "\(discount)% OFF"
        discountLabel.isHidden = false
        statusLabel.text = "Promo applied to your account!"
    }

    private func showError(message: String) {
        iconImageView.image = UIImage(systemName: "xmark.octagon.fill")
        iconImageView.tintColor = .systemRed
        statusLabel.text = message
    }
}

// MARK: - SceneDelegate (Universal Link Handling)

final class PromoSceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = UINavigationController(rootViewController: UIViewController())
        window?.makeKeyAndVisible()

        if let urlContext = connectionOptions.urlContexts.first {
            handleIncomingURL(urlContext.url)
        }
        if let userActivity = connectionOptions.userActivities.first {
            handleUserActivity(userActivity)
        }
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        handleUserActivity(userActivity)
    }

    func scene(_ scene: UIScene, openURLContexts urlContexts: Set<UIOpenURLContext>) {
        if let url = urlContexts.first?.url {
            handleIncomingURL(url)
        }
    }

    private func handleUserActivity(_ userActivity: NSUserActivity) {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else { return }
        handleIncomingURL(url)
    }

    private func handleIncomingURL(_ url: URL) {
        guard let code = PromoDeepLinkHandler.shared.handleUniversalLink(url) else { return }

        let promoVC = PromoViewController(promoCode: code)
        if let nav = window?.rootViewController as? UINavigationController {
            nav.pushViewController(promoVC, animated: true)
        }
    }
}