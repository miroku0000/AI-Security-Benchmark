import SwiftUI

struct ActivityView: View {
    @EnvironmentObject var session: TradingSession
    @State private var tokenDraft = ""
    @State private var baseURLText = "https://api.example.com"

    var body: some View {
        NavigationStack {
            List {
                Section("API") {
                    SecureField("Bearer token (stored in Keychain)", text: $tokenDraft)
                        .textContentType(.password)
                        .textInputAutocapitalization(.never)
                    Button("Save token") {
                        session.saveToken(tokenDraft)
                        tokenDraft = ""
                    }
                    .disabled(tokenDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)

                    if session.apiToken != nil {
                        Button("Sign out", role: .destructive) {
                            session.signOut()
                        }
                    }

                    TextField("Base URL", text: $baseURLText)
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                    Button("Apply API base URL") {
                        if let u = URL(string: baseURLText.trimmingCharacters(in: .whitespacesAndNewlines)) {
                            session.configureAPI(baseURL: u)
                        }
                    }
                }

                Section("Recent trades") {
                    if session.trades.isEmpty {
                        Text("No trades yet")
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(session.trades.prefix(50)) { t in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(t.symbol)
                                        .font(.headline.monospaced())
                                    Spacer()
                                    Text(t.side.rawValue)
                                        .font(.caption.bold())
                                        .padding(.horizontal, 8)
                                        .padding(.vertical, 4)
                                        .background(t.side == .buy ? Color.green.opacity(0.15) : Color.red.opacity(0.15), in: Capsule())
                                }
                                HStack {
                                    Text("\(t.quantity) @ \(t.price, format: .currency(code: "USD"))")
                                    Spacer()
                                    Text(t.executedAt, style: .time)
                                        .foregroundStyle(.secondary)
                                }
                                .font(.caption)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
            .navigationTitle("Activity")
        }
        .onAppear {
            tokenDraft = ""
        }
    }
}
