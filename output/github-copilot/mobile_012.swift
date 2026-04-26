import SwiftUI
import LocalAuthentication
import Security

@main
struct BiometricLoginApp: App {
    @StateObject private var authManager = AuthenticationManager()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(authManager)
        }
    }
}

@MainActor
final class AuthenticationManager: ObservableObject {
    enum AppState {
        case launching
        case login
        case authenticated
    }

    enum PasswordFieldTarget: Hashable {
        case username
        case password
    }

    struct AlertState: Identifiable {
        let id = UUID()
        let title: String
        let message: String
        let showRetry: Bool
    }

    @Published private(set) var appState: AppState = .launching
    @Published private(set) var biometricType: LABiometryType = .none
    @Published private(set) var isBusy = false
    @Published var username = ""
    @Published var password = ""
    @Published var inlineMessage: String?
    @Published var alertState: AlertState?

    private let sessionStore = BiometricSessionStore()
    private var didAttemptRestore = false

    init() {
        refreshBiometricType()
    }

    var biometricButtonTitle: String {
        switch biometricType {
        case .faceID:
            return "Continue with Face ID"
        case .touchID:
            return "Continue with Touch ID"
        default:
            return "Continue with Biometrics"
        }
    }

    var biometricDescription: String {
        switch biometricType {
        case .faceID:
            return "Use Face ID to sign in faster next time."
        case .touchID:
            return "Use Touch ID to sign in faster next time."
        default:
            return "Use biometrics to sign in faster next time."
        }
    }

    var biometricIconName: String {
        switch biometricType {
        case .faceID:
            return "faceid"
        case .touchID:
            return "touchid"
        default:
            return "lock.shield"
        }
    }

    var supportsBiometrics: Bool {
        biometricType != .none
    }

    func start() {
        guard !didAttemptRestore else { return }
        didAttemptRestore = true
        restoreSessionIfAvailable()
    }

    func refreshBiometricType() {
        let context = LAContext()
        var error: NSError?
        _ = context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)
        biometricType = context.biometryType
    }

    func restoreSessionIfAvailable() {
        refreshBiometricType()

        guard sessionStore.hasPersistedSession else {
            appState = .login
            return
        }

        Task {
            isBusy = true
            defer { isBusy = false }

            do {
                _ = try await sessionStore.unlockPersistedSession(
                    using: configuredContext(),
                    reason: unlockReason
                )
                inlineMessage = nil
                appState = .authenticated
            } catch {
                appState = .login
                presentBiometricFailure(error)
            }
        }
    }

    func signInWithBiometrics() {
        refreshBiometricType()

        guard supportsBiometrics else {
            inlineMessage = "Biometric authentication is not available on this device. Enter your password instead."
            appState = .login
            return
        }

        Task {
            isBusy = true
            defer { isBusy = false }

            let context = configuredContext()

            do {
                try await evaluateBiometrics(with: context)
                try sessionStore.persistAuthenticatedSession()
                inlineMessage = nil
                alertState = nil
                appState = .authenticated
            } catch {
                appState = .login
                presentBiometricFailure(error)
            }
        }
    }

    func signInWithPassword() {
        let trimmedUsername = username.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPassword = password.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedUsername.isEmpty, !trimmedPassword.isEmpty else {
            inlineMessage = "Enter your username and password."
            return
        }

        inlineMessage = nil
        alertState = nil
        appState = .authenticated
    }

    func usePasswordInstead() {
        alertState = nil
        inlineMessage = "Enter your password to continue."
        appState = .login
    }

    func logout() {
        sessionStore.clearPersistedSession()
        username = ""
        password = ""
        inlineMessage = nil
        alertState = nil
        appState = .login
    }

    private func configuredContext() -> LAContext {
        let context = LAContext()
        context.localizedCancelTitle = "Use Password"
        context.localizedFallbackTitle = "Enter Password"
        return context
    }

    private func evaluateBiometrics(with context: LAContext) async throws {
        var authError: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &authError) else {
            throw authError ?? LAError(.biometryNotAvailable)
        }

        try await withCheckedThrowingContinuation { continuation in
            context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: signInReason
            ) { success, error in
                if success {
                    continuation.resume(returning: ())
                } else {
                    continuation.resume(throwing: error ?? LAError(.authenticationFailed))
                }
            }
        }
    }

    private var signInReason: String {
        switch biometricType {
        case .faceID:
            return "Use Face ID to sign in to your account."
        case .touchID:
            return "Use Touch ID to sign in to your account."
        default:
            return "Use biometrics to sign in to your account."
        }
    }

    private var unlockReason: String {
        switch biometricType {
        case .faceID:
            return "Use Face ID to unlock your saved session."
        case .touchID:
            return "Use Touch ID to unlock your saved session."
        default:
            return "Use biometrics to unlock your saved session."
        }
    }

    private func presentBiometricFailure(_ error: Error) {
        let message = userFriendlyMessage(for: error)
        inlineMessage = message
        alertState = AlertState(
            title: "Authentication Unavailable",
            message: message,
            showRetry: supportsBiometrics
        )
    }

    private func userFriendlyMessage(for error: Error) -> String {
        guard let laError = error as? LAError else {
            return "We couldn't sign you in with biometrics. Try again or enter your password."
        }

        switch laError.code {
        case .authenticationFailed:
            return "Face ID or Touch ID didn't recognize you. Try again or enter your password."
        case .userCancel:
            return "Biometric sign-in was canceled. Try again or enter your password."
        case .userFallback:
            return "Enter your password to continue."
        case .systemCancel:
            return "Biometric sign-in was interrupted. Try again or enter your password."
        case .biometryNotAvailable:
            return "Biometric authentication is not available on this device. Enter your password instead."
        case .biometryNotEnrolled:
            return "Set up Face ID or Touch ID in Settings, or enter your password instead."
        case .biometryLockout:
            return "Face ID or Touch ID is locked right now. Enter your password to continue."
        case .passcodeNotSet:
            return "Set a device passcode before using Face ID or Touch ID. Enter your password instead."
        case .appCancel:
            return "Biometric sign-in was canceled by the app. Try again or enter your password."
        case .invalidContext, .notInteractive:
            return "Biometric sign-in isn't available right now. Enter your password instead."
        default:
            return "We couldn't sign you in with biometrics. Try again or enter your password."
        }
    }
}

struct RootView: View {
    @EnvironmentObject private var authManager: AuthenticationManager

    var body: some View {
        Group {
            switch authManager.appState {
            case .launching:
                LaunchView()
            case .login:
                LoginView()
            case .authenticated:
                HomeView()
            }
        }
        .task {
            authManager.start()
        }
    }
}

struct LaunchView: View {
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
                .progressViewStyle(.circular)
            Text("Checking your saved sign-in…")
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }
}

struct LoginView: View {
    @EnvironmentObject private var authManager: AuthenticationManager
    @FocusState private var focusedField: AuthenticationManager.PasswordFieldTarget?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 24) {
                    Spacer(minLength: 32)

                    Image(systemName: authManager.biometricIconName)
                        .font(.system(size: 60))
                        .foregroundStyle(.tint)

                    VStack(spacing: 8) {
                        Text("Welcome Back")
                            .font(.largeTitle.bold())
                        Text(authManager.biometricDescription)
                            .font(.subheadline)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.secondary)
                    }

                    if let inlineMessage = authManager.inlineMessage {
                        Text(inlineMessage)
                            .font(.footnote)
                            .multilineTextAlignment(.center)
                            .foregroundStyle(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }

                    VStack(spacing: 14) {
                        TextField("Username", text: $authManager.username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .textContentType(.username)
                            .padding()
                            .background(Color(.secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .focused($focusedField, equals: .username)

                        SecureField("Password", text: $authManager.password)
                            .textContentType(.password)
                            .padding()
                            .background(Color(.secondarySystemBackground))
                            .clipShape(RoundedRectangle(cornerRadius: 12))
                            .focused($focusedField, equals: .password)

                        Button {
                            authManager.signInWithPassword()
                        } label: {
                            Text("Sign In with Password")
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color.primary)
                                .foregroundStyle(Color(.systemBackground))
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                        }
                        .buttonStyle(.plain)
                        .disabled(authManager.isBusy)

                        if authManager.supportsBiometrics {
                            Button {
                                authManager.signInWithBiometrics()
                            } label: {
                                HStack(spacing: 10) {
                                    Image(systemName: authManager.biometricIconName)
                                    Text(authManager.biometricButtonTitle)
                                }
                                .font(.headline)
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color.accentColor)
                                .foregroundStyle(.white)
                                .clipShape(RoundedRectangle(cornerRadius: 12))
                            }
                            .buttonStyle(.plain)
                            .disabled(authManager.isBusy)
                        }
                    }

                    if authManager.isBusy {
                        ProgressView()
                            .padding(.top, 8)
                    }

                    Spacer(minLength: 32)
                }
                .padding(24)
            }
            .navigationTitle("Login")
            .alert(item: $authManager.alertState) { alert in
                if alert.showRetry {
                    return Alert(
                        title: Text(alert.title),
                        message: Text(alert.message),
                        primaryButton: .default(Text("Try Again")) {
                            authManager.signInWithBiometrics()
                        },
                        secondaryButton: .default(Text("Use Password")) {
                            authManager.usePasswordInstead()
                            focusedField = .password
                        }
                    )
                } else {
                    return Alert(
                        title: Text(alert.title),
                        message: Text(alert.message),
                        dismissButton: .default(Text("Use Password")) {
                            authManager.usePasswordInstead()
                            focusedField = .password
                        }
                    )
                }
            }
            .onAppear {
                authManager.refreshBiometricType()
                if authManager.username.isEmpty {
                    focusedField = .username
                } else {
                    focusedField = .password
                }
            }
        }
    }
}

struct HomeView: View {
    @EnvironmentObject private var authManager: AuthenticationManager

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "checkmark.shield.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(.green)

                Text("You're Signed In")
                    .font(.largeTitle.bold())

                Text("If you used Face ID or Touch ID, your secure sign-in session is saved and the login screen will be bypassed next time.")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)

                Button(role: .destructive) {
                    authManager.logout()
                } label: {
                    Text("Log Out")
                        .font(.headline)
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color.red)
                        .foregroundStyle(.white)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
                .buttonStyle(.plain)
                .padding(.top, 8)
            }
            .padding(24)
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .navigationTitle("Home")
        }
    }
}

struct KeychainSessionPayload {
    let value: Data
}

final class BiometricSessionStore {
    private let service = "com.github.copilot.biometric-login"
    private let account = "authenticated-session"

    var hasPersistedSession: Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnAttributes as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
            kSecUseAuthenticationUI as String: kSecUseAuthenticationUISkip
        ]

        let status = SecItemCopyMatching(query as CFDictionary, nil)
        return status == errSecSuccess || status == errSecInteractionNotAllowed
    }

    func persistAuthenticatedSession() throws {
        let data = Data("authenticated".utf8)
        var unmanagedError: Unmanaged<CFError>?
        guard let accessControl = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
            .biometryCurrentSet,
            &unmanagedError
        ) else {
            if let cfError = unmanagedError?.takeRetainedValue() {
                throw cfError as Error
            }
            throw BiometricSessionError.accessControlCreationFailed
        }

        let deleteQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(deleteQuery as CFDictionary)

        let addQuery: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecValueData as String: data,
            kSecAttrAccessControl as String: accessControl
        ]

        let status = SecItemAdd(addQuery as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw BiometricSessionError.keychainWriteFailed(status)
        }
    }

    func unlockPersistedSession(using context: LAContext, reason: String) async throws -> KeychainSessionPayload {
        try await withCheckedThrowingContinuation { continuation in
            DispatchQueue.global(qos: .userInitiated).async {
                var result: CFTypeRef?
                let query: [String: Any] = [
                    kSecClass as String: kSecClassGenericPassword,
                    kSecAttrService as String: self.service,
                    kSecAttrAccount as String: self.account,
                    kSecReturnData as String: true,
                    kSecMatchLimit as String: kSecMatchLimitOne,
                    kSecUseAuthenticationContext as String: context,
                    kSecUseOperationPrompt as String: reason
                ]

                let status = SecItemCopyMatching(query as CFDictionary, &result)

                switch status {
                case errSecSuccess:
                    if let data = result as? Data {
                        continuation.resume(returning: KeychainSessionPayload(value: data))
                    } else {
                        continuation.resume(throwing: BiometricSessionError.invalidPayload)
                    }
                case errSecUserCanceled:
                    continuation.resume(throwing: LAError(.userCancel))
                case errSecAuthFailed:
                    continuation.resume(throwing: LAError(.authenticationFailed))
                case errSecInteractionNotAllowed:
                    continuation.resume(throwing: LAError(.notInteractive))
                case errSecNotAvailable, errSecItemNotFound:
                    continuation.resume(throwing: LAError(.biometryNotAvailable))
                case errSecSystemCancel:
                    continuation.resume(throwing: LAError(.systemCancel))
                default:
                    continuation.resume(throwing: BiometricSessionError.keychainReadFailed(status))
                }
            }
        }
    }

    func clearPersistedSession() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }
}

enum BiometricSessionError: LocalizedError {
    case accessControlCreationFailed
    case keychainWriteFailed(OSStatus)
    case keychainReadFailed(OSStatus)
    case invalidPayload

    var errorDescription: String? {
        switch self {
        case .accessControlCreationFailed:
            return "Unable to prepare secure biometric storage."
        case .keychainWriteFailed(let status):
            return "Unable to save your biometric sign-in state. Keychain status: \(status)."
        case .keychainReadFailed(let status):
            return "Unable to restore your saved biometric sign-in state. Keychain status: \(status)."
        case .invalidPayload:
            return "Your saved biometric sign-in state is invalid."
        }
    }
}