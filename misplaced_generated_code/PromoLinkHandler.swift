import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    
    var window: UIWindow?
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        window = UIWindow(frame: UIScreen.main.bounds)
        let mainViewController = PromoViewController()
        let navigationController = UINavigationController(rootViewController: mainViewController)
        window?.rootViewController = navigationController
        window?.makeKeyAndVisible()
        return true
    }
    
    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let incomingURL = userActivity.webpageURL else {
            return false
        }
        
        handleUniversalLink(url: incomingURL)
        return true
    }
    
    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {
        handleUniversalLink(url: url)
        return true
    }
    
    private func handleUniversalLink(url: URL) {
        let linkHandler = PromoLinkHandler()
        linkHandler.processPromoLink(url: url)
    }
}

class PromoLinkHandler {
    
    struct PromoData {
        let code: String
        let discount: Int
    }
    
    func processPromoLink(url: URL) {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              url.host == "myapp.com",
              url.path == "/promo" else {
            return
        }
        
        var promoCode: String?
        var discountPercentage: Int?
        
        components.queryItems?.forEach { item in
            switch item.name {
            case "code":
                promoCode = item.value
            case "discount":
                if let value = item.value, let discount = Int(value) {
                    discountPercentage = discount
                }
            default:
                break
            }
        }
        
        if let code = promoCode, let discount = discountPercentage {
            let promoData = PromoData(code: code, discount: discount)
            applyPromoToAccount(promo: promoData)
        }
    }
    
    private func applyPromoToAccount(promo: PromoData) {
        PromoManager.shared.applyPromo(promo)
        
        NotificationCenter.default.post(
            name: .promoApplied,
            object: nil,
            userInfo: ["code": promo.code, "discount": promo.discount]
        )
    }
}

class PromoManager {
    static let shared = PromoManager()
    private init() {}
    
    private let userDefaults = UserDefaults.standard
    private let promoHistoryKey = "AppliedPromos"
    private let activePromoKey = "ActivePromo"
    
    func applyPromo(_ promo: PromoLinkHandler.PromoData) {
        var promoHistory = getPromoHistory()
        
        let promoEntry: [String: Any] = [
            "code": promo.code,
            "discount": promo.discount,
            "appliedDate": Date().timeIntervalSince1970
        ]
        
        promoHistory.append(promoEntry)
        userDefaults.set(promoHistory, forKey: promoHistoryKey)
        
        userDefaults.set(promoEntry, forKey: activePromoKey)
        userDefaults.synchronize()
        
        updateUserAccount(with: promo)
    }
    
    private func getPromoHistory() -> [[String: Any]] {
        return userDefaults.array(forKey: promoHistoryKey) as? [[String: Any]] ?? []
    }
    
    func getActivePromo() -> [String: Any]? {
        return userDefaults.dictionary(forKey: activePromoKey)
    }
    
    private func updateUserAccount(with promo: PromoLinkHandler.PromoData) {
        let accountManager = AccountManager.shared
        accountManager.applyDiscount(percentage: promo.discount, promoCode: promo.code)
    }
}

class AccountManager {
    static let shared = AccountManager()
    private init() {}
    
    private let accountKey = "UserAccount"
    private let userDefaults = UserDefaults.standard
    
    func applyDiscount(percentage: Int, promoCode: String) {
        var account = getCurrentAccount()
        account["activePromoCode"] = promoCode
        account["discountPercentage"] = percentage
        account["promoActivationDate"] = Date().timeIntervalSince1970
        
        if let currentBalance = account["balance"] as? Double {
            let discountAmount = currentBalance * (Double(percentage) / 100.0)
            account["discountedBalance"] = currentBalance - discountAmount
        }
        
        userDefaults.set(account, forKey: accountKey)
        userDefaults.synchronize()
    }
    
    func getCurrentAccount() -> [String: Any] {
        if let account = userDefaults.dictionary(forKey: accountKey) {
            return account
        }
        
        let defaultAccount: [String: Any] = [
            "userId": UUID().uuidString,
            "balance": 100.0,
            "createdDate": Date().timeIntervalSince1970
        ]
        
        userDefaults.set(defaultAccount, forKey: accountKey)
        return defaultAccount
    }
}

class PromoViewController: UIViewController {
    
    private let titleLabel = UILabel()
    private let promoStatusLabel = UILabel()
    private let codeLabel = UILabel()
    private let discountLabel = UILabel()
    private let balanceLabel = UILabel()
    private let instructionLabel = UILabel()
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        updatePromoDisplay()
        
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(promoApplied),
            name: .promoApplied,
            object: nil
        )
    }
    
    private func setupUI() {
        view.backgroundColor = .systemBackground
        navigationItem.title = "Promo Manager"
        
        titleLabel.text = "Marketing Campaign Promo System"
        titleLabel.font = .systemFont(ofSize: 20, weight: .bold)
        titleLabel.textAlignment = .center
        
        promoStatusLabel.font = .systemFont(ofSize: 16, weight: .medium)
        promoStatusLabel.textAlignment = .center
        promoStatusLabel.numberOfLines = 0
        
        codeLabel.font = .systemFont(ofSize: 18, weight: .semibold)
        codeLabel.textAlignment = .center
        codeLabel.textColor = .systemBlue
        
        discountLabel.font = .systemFont(ofSize: 24, weight: .bold)
        discountLabel.textAlignment = .center
        discountLabel.textColor = .systemGreen
        
        balanceLabel.font = .systemFont(ofSize: 16)
        balanceLabel.textAlignment = .center
        balanceLabel.numberOfLines = 0
        
        instructionLabel.text = "Test URL: https://myapp.com/promo?code=XYZ&discount=50"
        instructionLabel.font = .systemFont(ofSize: 12)
        instructionLabel.textAlignment = .center
        instructionLabel.textColor = .secondaryLabel
        instructionLabel.numberOfLines = 0
        
        let stackView = UIStackView(arrangedSubviews: [
            titleLabel,
            UIView(),
            promoStatusLabel,
            codeLabel,
            discountLabel,
            balanceLabel,
            UIView(),
            instructionLabel
        ])
        
        stackView.axis = .vertical
        stackView.spacing = 20
        stackView.translatesAutoresizingMaskIntoConstraints = false
        
        view.addSubview(stackView)
        
        NSLayoutConstraint.activate([
            stackView.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 20),
            stackView.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -20),
            stackView.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }
    
    @objc private func promoApplied(_ notification: Notification) {
        DispatchQueue.main.async {
            self.updatePromoDisplay()
        }
    }
    
    private func updatePromoDisplay() {
        let accountManager = AccountManager.shared
        let account = accountManager.getCurrentAccount()
        
        if let activePromo = PromoManager.shared.getActivePromo(),
           let code = activePromo["code"] as? String,
           let discount = activePromo["discount"] as? Int {
            
            promoStatusLabel.text = "✅ Promo Active"
            promoStatusLabel.textColor = .systemGreen
            
            codeLabel.text = "Code: \(code)"
            discountLabel.text = "\(discount)% OFF"
            
            if let originalBalance = account["balance"] as? Double,
               let discountedBalance = account["discountedBalance"] as? Double {
                balanceLabel.text = String(format: "Original: $%.2f\nDiscounted: $%.2f", originalBalance, discountedBalance)
            }
        } else {
            promoStatusLabel.text = "No Active Promo"
            promoStatusLabel.textColor = .secondaryLabel
            codeLabel.text = ""
            discountLabel.text = ""
            
            if let balance = account["balance"] as? Double {
                balanceLabel.text = String(format: "Balance: $%.2f", balance)
            }
        }
    }
}

extension Notification.Name {
    static let promoApplied = Notification.Name("PromoApplied")
}