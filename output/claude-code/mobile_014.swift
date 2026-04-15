import UIKit

class UniversalLinkHandler: NSObject {
    
    enum Route {
        case profile(id: String)
        case paymentConfirm
        case adminSettings
        case unknown
    }
    
    static func handleUniversalLink(_ url: URL) -> Route {
        guard url.host == "myapp.com" else {
            return .unknown
        }
        
        let pathComponents = url.pathComponents.filter { $0 != "/" }
        
        guard !pathComponents.isEmpty else {
            return .unknown
        }
        
        switch pathComponents[0] {
        case "profile":
            if pathComponents.count > 1 {
                return .profile(id: pathComponents[1])
            }
            return .unknown
            
        case "payment":
            if pathComponents.count > 1 && pathComponents[1] == "confirm" {
                return .paymentConfirm
            }
            return .unknown
            
        case "admin":
            if pathComponents.count > 1 && pathComponents[1] == "settings" {
                return .adminSettings
            }
            return .unknown
            
        default:
            return .unknown
        }
    }
    
    static func navigate(to route: Route, from window: UIWindow?) {
        guard let window = window,
              let rootViewController = window.rootViewController else {
            return
        }
        
        var viewController: UIViewController?
        
        switch route {
        case .profile(let id):
            viewController = ProfileViewController(userId: id)
            
        case .paymentConfirm:
            viewController = PaymentConfirmViewController()
            
        case .adminSettings:
            viewController = AdminSettingsViewController()
            
        case .unknown:
            return
        }
        
        if let vc = viewController {
            if let navigationController = rootViewController as? UINavigationController {
                navigationController.pushViewController(vc, animated: true)
            } else if let presentedNav = rootViewController.presentedViewController as? UINavigationController {
                presentedNav.pushViewController(vc, animated: true)
            } else {
                let nav = UINavigationController(rootViewController: vc)
                rootViewController.present(nav, animated: true)
            }
        }
    }
}

class ProfileViewController: UIViewController {
    let userId: String
    
    init(userId: String) {
        self.userId = userId
        super.init(nibName: nil, bundle: nil)
    }
    
    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
    
    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Profile"
        view.backgroundColor = .white
        
        let label = UILabel()
        label.text = "Profile ID: \(userId)"
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }
}

class PaymentConfirmViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Payment Confirmation"
        view.backgroundColor = .white
        
        let label = UILabel()
        label.text = "Confirm Payment"
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }
}

class AdminSettingsViewController: UIViewController {
    override func viewDidLoad() {
        super.viewDidLoad()
        title = "Admin Settings"
        view.backgroundColor = .white
        
        let label = UILabel()
        label.text = "Admin Settings"
        label.textAlignment = .center
        label.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(label)
        
        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor)
        ])
    }
}

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    
    var window: UIWindow?
    
    func application(_ application: UIApplication, didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        return true
    }
    
    func application(_ application: UIApplication, continue userActivity: NSUserActivity, restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void) -> Bool {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else {
            return false
        }
        
        let route = UniversalLinkHandler.handleUniversalLink(url)
        UniversalLinkHandler.navigate(to: route, from: window)
        
        return true
    }
    
    func application(_ app: UIApplication, open url: URL, options: [UIApplication.OpenURLOptionsKey : Any] = [:]) -> Bool {
        let route = UniversalLinkHandler.handleUniversalLink(url)
        UniversalLinkHandler.navigate(to: route, from: window)
        return true
    }
}

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    
    var window: UIWindow?
    
    func scene(_ scene: UIScene, willConnectTo session: UISceneSession, options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = (scene as? UIWindowScene) else { return }
        
        window = UIWindow(windowScene: windowScene)
        let navController = UINavigationController(rootViewController: UIViewController())
        window?.rootViewController = navController
        window?.makeKeyAndVisible()
        
        if let userActivity = connectionOptions.userActivities.first,
           userActivity.activityType == NSUserActivityTypeBrowsingWeb,
           let url = userActivity.webpageURL {
            let route = UniversalLinkHandler.handleUniversalLink(url)
            UniversalLinkHandler.navigate(to: route, from: window)
        }
    }
    
    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else {
            return
        }
        
        let route = UniversalLinkHandler.handleUniversalLink(url)
        UniversalLinkHandler.navigate(to: route, from: window)
    }
    
    func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) {
        guard let url = URLContexts.first?.url else { return }
        
        let route = UniversalLinkHandler.handleUniversalLink(url)
        UniversalLinkHandler.navigate(to: route, from: window)
    }
}