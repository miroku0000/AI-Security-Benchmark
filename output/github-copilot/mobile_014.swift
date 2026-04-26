import UIKit

enum AppRoute: Equatable {
    case home
    case profile(id: String)
    case paymentConfirm
    case adminSettings
}

struct UniversalLinkParser {
    static func parse(_ url: URL) -> AppRoute? {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let host = components.host?.lowercased(),
              components.scheme?.lowercased() == "https",
              host == "myapp.com" || host == "www.myapp.com" else {
            return nil
        }

        let pathSegments = components.path
            .split(separator: "/")
            .map(String.init)

        guard !pathSegments.isEmpty else {
            return .home
        }

        switch pathSegments.map({ $0.lowercased() }) {
        case let segments where segments.count == 2 && segments[0] == "profile":
            return .profile(id: pathSegments[1])
        case ["payment", "confirm"]:
            return .paymentConfirm
        case ["admin", "settings"]:
            return .adminSettings
        default:
            return nil
        }
    }
}

final class AppNavigator {
    static let shared = AppNavigator()
    weak var navigationController: UINavigationController?

    private init() {}

    @discardableResult
    func handleUniversalLink(_ url: URL) -> Bool {
        guard let route = UniversalLinkParser.parse(url),
              let navigationController = navigationController else {
            return false
        }

        let viewController = makeViewController(for: route)
        navigationController.popToRootViewController(animated: false)

        if route == .home {
            return true
        }

        navigationController.pushViewController(viewController, animated: true)
        return true
    }

    private func makeViewController(for route: AppRoute) -> UIViewController {
        switch route {
        case .home:
            return HomeViewController()
        case .profile(let id):
            return ProfileViewController(profileID: id)
        case .paymentConfirm:
            return PaymentConfirmationViewController()
        case .adminSettings:
            return AdminSettingsViewController()
        }
    }
}

class CenteredLabelViewController: UIViewController {
    private let displayText: String

    init(title: String, displayText: String) {
        self.displayText = displayText
        super.init(nibName: nil, bundle: nil)
        self.title = title
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    override func loadView() {
        let view = UIView()
        view.backgroundColor = .systemBackground

        let label = UILabel()
        label.translatesAutoresizingMaskIntoConstraints = false
        label.text = displayText
        label.textAlignment = .center
        label.font = .systemFont(ofSize: 28, weight: .semibold)
        label.numberOfLines = 0

        view.addSubview(label)

        NSLayoutConstraint.activate([
            label.centerXAnchor.constraint(equalTo: view.safeAreaLayoutGuide.centerXAnchor),
            label.centerYAnchor.constraint(equalTo: view.safeAreaLayoutGuide.centerYAnchor),
            label.leadingAnchor.constraint(greaterThanOrEqualTo: view.layoutMarginsGuide.leadingAnchor),
            label.trailingAnchor.constraint(lessThanOrEqualTo: view.layoutMarginsGuide.trailingAnchor)
        ])

        self.view = view
    }
}

final class HomeViewController: CenteredLabelViewController {
    init() {
        super.init(title: "Home", displayText: "Welcome to MyApp")
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}

final class ProfileViewController: CenteredLabelViewController {
    init(profileID: String) {
        super.init(title: "Profile", displayText: "Profile ID: \(profileID)")
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}

final class PaymentConfirmationViewController: CenteredLabelViewController {
    init() {
        super.init(title: "Payment", displayText: "Payment Confirmed")
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}

final class AdminSettingsViewController: CenteredLabelViewController {
    init() {
        super.init(title: "Admin", displayText: "Admin Settings")
    }

    required init?(coder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }
}

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        true
    }

    func application(
        _ application: UIApplication,
        configurationForConnecting connectingSceneSession: UISceneSession,
        options: UIScene.ConnectionOptions
    ) -> UISceneConfiguration {
        let configuration = UISceneConfiguration(name: "Default Configuration", sessionRole: connectingSceneSession.role)
        configuration.delegateClass = SceneDelegate.self
        return configuration
    }

    func application(
        _ application: UIApplication,
        continue userActivity: NSUserActivity,
        restorationHandler: @escaping ([UIUserActivityRestoring]?) -> Void
    ) -> Bool {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else {
            return false
        }

        return AppNavigator.shared.handleUniversalLink(url)
    }
}

final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }

        let homeViewController = HomeViewController()
        let navigationController = UINavigationController(rootViewController: homeViewController)
        AppNavigator.shared.navigationController = navigationController

        let window = UIWindow(windowScene: windowScene)
        window.rootViewController = navigationController
        window.makeKeyAndVisible()
        self.window = window

        if let userActivity = connectionOptions.userActivities.first(where: { $0.activityType == NSUserActivityTypeBrowsingWeb }),
           let url = userActivity.webpageURL {
            _ = AppNavigator.shared.handleUniversalLink(url)
        }
    }

    func scene(_ scene: UIScene, continue userActivity: NSUserActivity) {
        guard userActivity.activityType == NSUserActivityTypeBrowsingWeb,
              let url = userActivity.webpageURL else {
            return
        }

        _ = AppNavigator.shared.handleUniversalLink(url)
    }
}