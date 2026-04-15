import SwiftUI

struct SettingsView: View {
    @Environment(TradingEngine.self) private var engine
    @State private var tokenInput = ""

    var body: some View {
        NavigationStack {
            Form {
                Section("Secure session") {
                    if engine.sessionTokenSet {
                        Label("API token stored in Keychain", systemImage: "lock.fill")
                            .foregroundStyle(.secondary)
                        Button("Sign out", role: .destructive) {
                            engine.signOut()
                        }
                    } else {
                        SecureField("Paste access token", text: $tokenInput)
                        Button("Save token") {
                            do {
                                try engine.setSessionToken(tokenInput)
                                tokenInput = ""
                            } catch {}
                        }
                        .disabled(tokenInput.isEmpty)
                    }
                }
                Section("Backend") {
                    Text("Set TRADE_API_BASE_URL and optional TRADE_WS_URL in Info.plist for live API and websocket.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Account")
        }
    }
}
