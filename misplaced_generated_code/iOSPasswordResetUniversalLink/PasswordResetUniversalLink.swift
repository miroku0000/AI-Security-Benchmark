import SwiftUI

// MARK: - URL parsing

struct PasswordResetLinkParser {
    private let allowedHosts: Set<String>
    private let resetPathComponents: [String]

    init(allowedHosts: Set<String> = ["myapp.com", "www.myapp.com"], resetPath: String = "/reset-password") {
        self.allowedHosts = allowedHosts
        let trimmed = resetPath.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        self.resetPathComponents = trimmed.split(separator: "/").map(String.init)
    }

    func token(from url: URL) -> String? {
        guard let host = url.host?.lowercased(), allowedHosts.contains(host) else { return nil }
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return nil }
        let pathParts = components.path.split(separator: "/").map(String.init)
        guard pathParts == resetPathComponents else { return nil }
        return components.queryItems?.first(where: { $0.name == "token" })?.value.flatMap { $0.isEmpty ? nil : $0 }
    }
}

// MARK: - Navigation

enum AppRoute: Hashable {
    case resetPassword(token: String)
}

@MainActor
final class AppRouter: ObservableObject {
    @Published var path = NavigationPath()
    private let parser = PasswordResetLinkParser()

    func handleIncomingURL(_ url: URL) {
        guard let token = parser.token(from: url) else { return }
        path = NavigationPath()
        path.append(AppRoute.resetPassword(token: token))
    }
}

// MARK: - Views

struct ResetPasswordView: View {
    let token: String
    @State private var newPassword: String = ""
    @State private var confirmPassword: String = ""

    var body: some View {
        Form {
            Section {
                Text("Enter a new password for your account.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Section("Recovery token") {
                Text(token)
                    .font(.footnote.monospaced())
                    .textSelection(.enabled)
            }
            Section("New password") {
                SecureField("New password", text: $newPassword)
                SecureField("Confirm password", text: $confirmPassword)
            }
            Section {
                Button("Update password") {
                    // Submit token + newPassword to your account recovery API.
                }
                .disabled(newPassword.isEmpty || newPassword != confirmPassword)
            }
        }
        .navigationTitle("Reset password")
        .navigationBarTitleDisplayMode(.inline)
    }
}

struct RootView: View {
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        NavigationStack(path: $router.path) {
            ContentUnavailableView(
                "Account",
                systemImage: "person.crop.circle",
                description: Text("Open your password reset link from email to continue.")
            )
            .navigationTitle("MyApp")
            .navigationDestination(for: AppRoute.self) { route in
                switch route {
                case .resetPassword(let token):
                    ResetPasswordView(token: token)
                }
            }
        }
    }
}

@main
struct PasswordResetUniversalLinkApp: App {
    @StateObject private var router = AppRouter()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(router)
                .onOpenURL { url in
                    router.handleIncomingURL(url)
                }
                .onContinueUserActivity(NSUserActivityTypeBrowsingWeb) { userActivity in
                    if let url = userActivity.webpageURL {
                        router.handleIncomingURL(url)
                    }
                }
        }
    }
}
