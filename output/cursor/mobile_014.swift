import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    // Fallback for iOS 12 and earlier (or when SceneDelegate is not used)
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {

        if #available(iOS 13.0, *) {
            // SceneDelegate will handle window
        } else {
            let window = UIWindow(frame: UIScreen.main.bounds)
            let rootVC = RootViewController()
            let nav = UINavigationController(rootViewController: rootVC)
            window.rootViewController = nav
            window.makeKeyAndVisible()
            self.window = window
        }

        return true
    }

    // Universal link handling for iOS 12 and earlier
    func application(
        _ application: UIApplication,
        continue userActivity: NSUserActivity,
        restorationHandler: @escaping ([UIUserActivityRestoring]?
        ) -> Void
    ) -> Bool {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let incomingURL = userActivity.webpageURL else {
            return false
        }

        return handleIncomingURL(incomingURL, fromSceneDelegate: false)
    }

    private func handleIncomingURL(_ url: URL, fromSceneDelegate: Bool) -> Bool {
        guard let host = url.host, host == "myapp.com" else {
            return false
        }

        let pathComponents = url.pathComponents.filter { $0 != "/" }
        guard !pathComponents.isEmpty else { return false }

        let navController: UINavigationController?

        if #available(iOS 13.0, *) {
            if fromSceneDelegate {
                navController = (UIApplication.shared.connectedScenes.first { $0.activationState == .foregroundActive } as? UIWindowScene)?
                    .windows
                    .first { $0.isKeyWindow }?
                    .rootViewController as? UINavigationController
            } else {
                navController = window?.rootViewController as? UINavigationController
            }
        } else {
            navController = window?.rootViewController as? UINavigationController
        }

        guard let navigationController = navController else {
            return false
        }

        // Routing
        if pathComponents.count >= 2 && pathComponents[0] == "profile" {
            let userId = pathComponents[1]
            let vc = ProfileViewController(userId: userId)
            navigationController.popToRootViewController(animated: false)
            navigationController.pushViewController(vc, animated: true)
            return true
        } else if pathComponents.count >= 2 && pathComponents[0] == "payment" && pathComponents[1] == "confirm" {
            let vc = PaymentConfirmViewController()
            navigationController.popToRootViewController(animated: false)
            navigationController.pushViewController(vc, animated: true)
            return true
        } else if pathComponents.count >= 2 && pathComponents[0] == "admin" && pathComponents[1] == "settings" {
            let vc = AdminSettingsViewController()
            navigationController.popToRootViewController(animated: false)
            navigationController.pushViewController(vc, animated: true)
            return true
        }

        return false
    }
}

@available(iOS 13.0, *)
class SceneDelegate: UIResponder, UIWindowSceneDelegate {

    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = (scene as? UIWindowScene) else { return }

        let window = UIWindow(windowScene: windowScene)
        let rootVC = RootViewController()
        let nav = UINavigationController(rootViewController: rootVC)
        window.rootViewController = nav
        window.makeKeyAndVisible()
        self.window = window

        if let userActivity = connectionOptions.userActivities.first(where: { $0.activityType == NSUserActivityTypeBrowsingWeb }),
           let incomingURL = userActivity.webpageURL {
            _ = handleIncomingURL(incomingURL)
        }
    }

    func scene(
        _ scene: UIScene,
        continue userActivity: NSUserActivity
    ) {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let incomingURL = userActivity.webpageURL else { return }

        _ = handleIncomingURL(incomingURL)
    }

    private func handleIncomingURL(_ url: URL) -> Bool {
        guard let host = url.host, host == "myapp.com" else {
            return false
        }

        let pathComponents = url.pathComponents.filter { $0 != "/" }
        guard !pathComponents.isEmpty else { return false }

        guard let navController = window?.rootViewController as? UINavigationController else {
            return false
        }

        if pathComponents.count >= 2 && pathComponents[0] == "profile" {
            let userId = pathComponents[1]
            let vc = ProfileViewController(userId: userId)
            navController.popToRootViewController(animated: false)
            navController.pushViewController(vc, animated: true)
            return true
        } else if pathComponents.count >= 2 && pathComponents[0] == "payment" && pathComponents[1] == "confirm" {
            let vc = PaymentConfirmViewController()
            navController.popToRootViewController(animated: false)
            navController.pushViewController(vc, animated: true)
            return true
        } else if pathComponents.count >= 2 && pathComponents[0] == "admin" && pathComponents[1] == "settings" {
            let vc = AdminSettingsViewController()
            navController.popToRootViewController(animated: false)
            navController.pushViewController(vc, animated: true)
            return true
        }

        return false
    }
}

class RootViewController: UIViewController {

    private let infoLabel: UILabel = {
        let label = UILabel()
        label.text = "Root View Controller\n(Open a universal link to navigate)"
        label.textAlignment = .center
        label.numberOfLines = 0
        label.textColor = .label
        return label
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        title = "MyApp"

        view.addSubview(infoLabel)
        infoLabel.translatesAutoresizingMaskIntoConstraints = false

        NSLayoutConstraint.activate([
            infoLabel.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            infoLabel.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            infoLabel.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 20),
            infoLabel.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -20)
        ])
    }
}

class ProfileViewController: UIViewController {

    private let userId: String

    private let label: UILabel = {
        let label = UILabel()
        label.textAlignment = .center
        label.numberOfLines = 0
        label.textColor = .label
        return label
    }()

    init(userId: String) {
        self.userId = userId
        super.init(nibName: nil, bundle: nil)
        title = "Profile"
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground

        view.addSubview(label)
        label.translatesAutoresizingMaskIntoConstraints = false
        label.text = "Profile View Controller\nUser ID: \(userId)"

        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            label.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -20)
        ])
    }
}

class PaymentConfirmViewController: UIViewController {

    private let label: UILabel = {
        let label = UILabel()
        label.text = "Payment Confirmation View Controller"
        label.textAlignment = .center
        label.numberOfLines = 0
        label.textColor = .label
        return label
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        title = "Payment Confirm"

        view.addSubview(label)
        label.translatesAutoresizingMaskIntoConstraints = false

        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            label.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -20)
        ])
    }
}

class AdminSettingsViewController: UIViewController {

    private let label: UILabel = {
        let label = UILabel()
        label.text = "Admin Settings View Controller"
        label.textAlignment = .center
        label.numberOfLines = 0
        label.textColor = .label
        return label
    }()

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = .systemBackground
        title = "Admin Settings"

        view.addSubview(label)
        label.translatesAutoresizingMaskIntoConstraints = false

        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.centerYAnchor),
            label.leadingAnchor.constraint(greaterThanOrEqualTo: view.leadingAnchor, constant: 20),
            label.trailingAnchor.constraint(lessThanOrEqualTo: view.trailingAnchor, constant: -20)
        ])
    }
}