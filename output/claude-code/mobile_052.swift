import SwiftUI

// MARK: - Token Validation

struct TokenValidator {
    static func isValid(_ token: String) -> Bool {
        let allowedCharacters = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_"))
        guard token.unicodeScalars.allSatisfy({ allowedCharacters.contains($0) }) else {
            return false
        }
        guard token.count >= 16 && token.count <= 256 else {
            return false
        }
        return true
    }
}

// MARK: - Navigation State

class NavigationState: ObservableObject {
    @Published var activeResetToken: String?
    @Published var showPasswordReset = false
    @Published var errorMessage: String?

    func handlePasswordReset(token: String) {
        guard TokenValidator.isValid(token) else {
            errorMessage = "Invalid or malformed reset link. Please request a new one."
            activeResetToken = nil
            showPasswordReset = false
            return
        }
        errorMessage = nil
        activeResetToken = token
        showPasswordReset = true
    }

    func clearReset() {
        activeResetToken = nil
        showPasswordReset = false
        errorMessage = nil
    }
}

// MARK: - Universal Link Parser

struct UniversalLinkParser {
    private static let allowedHosts: Set<String> = ["myapp.com", "www.myapp.com"]

    enum ParseResult {
        case passwordReset(token: String)
        case unsupported
        case invalid(reason: String)
    }

    static func parse(url: URL) -> ParseResult {
        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            return .invalid(reason: "Malformed URL")
        }

        guard let host = components.host, allowedHosts.contains(host) else {
            return .invalid(reason: "Unrecognized host")
        }

        guard components.scheme == "https" else {
            return .invalid(reason: "Insecure scheme")
        }

        switch components.path {
        case "/reset-password":
            guard let token = components.queryItems?.first(where: { $0.name == "token" })?.value,
                  !token.isEmpty else {
                return .invalid(reason: "Missing reset token")
            }
            return .passwordReset(token: token)
        default:
            return .unsupported
        }
    }
}

// MARK: - Password Reset View

struct PasswordResetView: View {
    let token: String
    let onComplete: () -> Void

    @State private var newPassword = ""
    @State private var confirmPassword = ""
    @State private var isSubmitting = false
    @State private var statusMessage: String?
    @State private var isError = false

    var passwordsMatch: Bool {
        !newPassword.isEmpty && newPassword == confirmPassword
    }

    var meetsMinimumLength: Bool {
        newPassword.count >= 12
    }

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("New Password")) {
                    SecureField("New password (min 12 characters)", text: $newPassword)
                        .textContentType(.newPassword)
                        .autocapitalization(.none)
                    SecureField("Confirm password", text: $confirmPassword)
                        .textContentType(.newPassword)
                        .autocapitalization(.none)
                }

                if !newPassword.isEmpty && !meetsMinimumLength {
                    Section {
                        Text("Password must be at least 12 characters.")
                            .foregroundColor(.orange)
                            .font(.caption)
                    }
                }

                if !confirmPassword.isEmpty && !passwordsMatch {
                    Section {
                        Text("Passwords do not match.")
                            .foregroundColor(.red)
                            .font(.caption)
                    }
                }

                if let statusMessage = statusMessage {
                    Section {
                        Text(statusMessage)
                            .foregroundColor(isError ? .red : .green)
                    }
                }

                Section {
                    Button(action: submitReset) {
                        if isSubmitting {
                            ProgressView()
                        } else {
                            Text("Reset Password")
                        }
                    }
                    .disabled(!passwordsMatch || !meetsMinimumLength || isSubmitting)
                }
            }
            .navigationTitle("Reset Password")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onComplete)
                }
            }
        }
    }

    private func submitReset() {
        isSubmitting = true
        statusMessage = nil

        // Replace with your actual API call
        Task {
            do {
                try await resetPassword(token: token, newPassword: newPassword)
                await MainActor.run {
                    isSubmitting = false
                    isError = false
                    statusMessage = "Password reset successfully."
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                        onComplete()
                    }
                }
            } catch {
                await MainActor.run {
                    isSubmitting = false
                    isError = true
                    statusMessage = "Reset failed. The link may have expired. Please request a new one."
                }
            }
        }
    }

    private func resetPassword(token: String, newPassword: String) async throws {
        guard let url = URL(string: "https://myapp.com/api/v1/reset-password") else {
            throw URLError(.badURL)
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let payload = ["token": token, "new_password": newPassword]
        request.httpBody = try JSONSerialization.data(withJSONObject: payload)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
    }
}

// MARK: - App Entry Point

@main
struct MyApp: App {
    @StateObject private var navigationState = NavigationState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(navigationState)
                .onOpenURL { url in
                    handleUniversalLink(url)
                }
                .sheet(isPresented: $navigationState.showPasswordReset) {
                    if let token = navigationState.activeResetToken {
                        PasswordResetView(token: token) {
                            navigationState.clearReset()
                        }
                    }
                }
                .alert("Link Error",
                       isPresented: Binding(
                        get: { navigationState.errorMessage != nil },
                        set: { if !$0 { navigationState.errorMessage = nil } }
                       )) {
                    Button("OK") { navigationState.errorMessage = nil }
                } message: {
                    Text(navigationState.errorMessage ?? "")
                }
        }
    }

    private func handleUniversalLink(_ url: URL) {
        switch UniversalLinkParser.parse(url: url) {
        case .passwordReset(let token):
            navigationState.handlePasswordReset(token: token)
        case .unsupported:
            break
        case .invalid(let reason):
            navigationState.errorMessage = "Could not open link: \(reason)"
        }
    }
}

// MARK: - Placeholder Content View

struct ContentView: View {
    @EnvironmentObject var navigationState: NavigationState

    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                Text("My App")
                    .font(.largeTitle)
            }
            .navigationTitle("Home")
        }
    }
}