import SwiftUI
import LocalAuthentication

@main
struct BiometricAuthApp: App {
    @StateObject private var appState = AppState()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(appState)
                .onAppear {
                    appState.tryBiometricOnLaunch()
                }
        }
    }
}

final class AppState: ObservableObject {
    @AppStorage("isUserAuthenticated") private var storedIsAuthenticated: Bool = false
    @AppStorage("isBiometricEnabled") private var storedIsBiometricEnabled: Bool = false

    @Published var isAuthenticated: Bool = false
    @Published var isBiometricEnabled: Bool = false

    private let authManager = BiometricAuthManager()

    init() {
        isAuthenticated = storedIsAuthenticated
        isBiometricEnabled = storedIsBiometricEnabled
    }

    func setAuthenticated(_ value: Bool) {
        isAuthenticated = value
        storedIsAuthenticated = value
    }

    func setBiometricEnabled(_ value: Bool) {
        isBiometricEnabled = value
        storedIsBiometricEnabled = value
    }

    func tryBiometricOnLaunch() {
        guard isBiometricEnabled, !isAuthenticated else { return }
        authManager.authenticateWithBiometrics(reason: "Unlock your account") { [weak self] success, _ in
            DispatchQueue.main.async {
                if success {
                    self?.setAuthenticated(true)
                }
            }
        }
    }

    func authenticateWithBiometrics(completion: @escaping (Bool, Error?) -> Void) {
        authManager.authenticateWithBiometrics(reason: "Authenticate to continue") { [weak self] success, error in
            DispatchQueue.main.async {
                if success {
                    self?.setAuthenticated(true)
                }
                completion(success, error)
            }
        }
    }
}

final class BiometricAuthManager {
    func authenticateWithBiometrics(reason: String, completion: @escaping (Bool, Error?) -> Void) {
        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            completion(false, error)
            return
        }

        context.evaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, localizedReason: reason) { success, evaluateError in
            completion(success, evaluateError)
        }
    }
}

struct ContentView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        Group {
            if appState.isAuthenticated {
                MainView()
            } else {
                LoginView()
            }
        }
        .animation(.default, value: appState.isAuthenticated)
    }
}

struct LoginView: View {
    @EnvironmentObject var appState: AppState

    @State private var username: String = ""
    @State private var password: String = ""
    @State private var showBiometricErrorAlert = false
    @State private var biometricErrorMessage: String = ""
    @State private var hasAttemptedBiometricOnAppear = false

    var body: some View {
        VStack(spacing: 24) {
            Text("Welcome")
                .font(.largeTitle)
                .bold()

            VStack(alignment: .leading, spacing: 12) {
                TextField("Username", text: $username)
                    .textContentType(.username)
                    .textInputAutocapitalization(.never)
                    .disableAutocorrection(true)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(8)

                SecureField("Password", text: $password)
                    .textContentType(.password)
                    .padding()
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(8)
            }

            Button(action: handlePasswordLogin) {
                Text("Log In")
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.accentColor)
                    .foregroundColor(.white)
                    .cornerRadius(8)
            }
            .disabled(username.isEmpty || password.isEmpty)

            if canUseBiometrics {
                VStack(alignment: .leading, spacing: 8) {
                    Button(action: attemptBiometricAuth) {
                        HStack {
                            Image(systemName: "faceid")
                            Text("Use Face ID / Touch ID")
                        }
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color(.tertiarySystemBackground))
                        .cornerRadius(8)
                    }

                    Toggle(isOn: Binding(
                        get: { appState.isBiometricEnabled },
                        set: { appState.setBiometricEnabled($0) }
                    )) {
                        Text("Enable biometric login next time")
                    }
                }
            }

            Spacer()
        }
        .padding()
        .onAppear {
            if !hasAttemptedBiometricOnAppear {
                hasAttemptedBiometricOnAppear = true
                if appState.isBiometricEnabled {
                    attemptBiometricAuth()
                }
            }
        }
        .alert("Biometric Authentication Failed", isPresented: $showBiometricErrorAlert) {
            Button("Try Again") {
                attemptBiometricAuth()
            }
            Button("Enter Password", role: .cancel) { }
        } message: {
            Text(biometricErrorMessage.isEmpty ? "You can try again or use your password." : biometricErrorMessage)
        }
    }

    private var canUseBiometrics: Bool {
        let context = LAContext()
        return context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: nil)
    }

    private func attemptBiometricAuth() {
        appState.authenticateWithBiometrics { success, error in
            if !success {
                biometricErrorMessage = (error as NSError?)?.localizedDescription ?? ""
                showBiometricErrorAlert = true
            }
        }
    }

    private func handlePasswordLogin() {
        // Replace this with your real credential validation.
        // For demo purposes, any non-empty username/password will succeed.
        appState.setAuthenticated(true)
        if canUseBiometrics {
            appState.setBiometricEnabled(true)
        }
    }
}

struct MainView: View {
    @EnvironmentObject var appState: AppState

    var body: some View {
        NavigationView {
            VStack(spacing: 24) {
                Text("You are logged in.")
                    .font(.title2)

                Button(role: .destructive) {
                    appState.setAuthenticated(false)
                } label: {
                    Text("Log Out")
                        .frame(maxWidth: .infinity)
                        .padding()
                        .background(Color(.systemRed))
                        .foregroundColor(.white)
                        .cornerRadius(8)
                }

                Toggle(isOn: Binding(
                    get: { appState.isBiometricEnabled },
                    set: { appState.setBiometricEnabled($0) }
                )) {
                    Text("Use Face ID / Touch ID next time")
                }

                Spacer()
            }
            .padding()
            .navigationTitle("Home")
        }
    }
}