import SwiftUI

struct ContentView: View {
    @StateObject private var client = APIClient()
    @State private var secureResult: String = "—"
    @State private var legacyResult: String = "—"
    @State private var isLoading = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Secure: https://api.example.com")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(secureResult)
                    .font(.body.monospaced())
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8)
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                Text("Legacy: http://legacy.internal")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text(legacyResult)
                    .font(.body.monospaced())
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8)
                    .background(Color(.secondarySystemBackground))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                Button(action: refreshAll) {
                    if isLoading {
                        ProgressView()
                    } else {
                        Text("Refresh both")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(isLoading)
            }
            .padding()
            .navigationTitle("API Clients")
        }
    }

    private func refreshAll() {
        isLoading = true
        Task {
            async let secure: String = {
                do {
                    let (data, resp) = try await client.fetchSecureStatus()
                    let body = String(data: data, encoding: .utf8) ?? "<binary \(data.count) bytes>"
                    return "HTTP \(resp.statusCode)\n\(body)"
                } catch {
                    return "Error: \(error.localizedDescription)"
                }
            }()
            async let legacy: String = {
                do {
                    let (data, resp) = try await client.fetchLegacyStatus()
                    let body = String(data: data, encoding: .utf8) ?? "<binary \(data.count) bytes>"
                    return "HTTP \(resp.statusCode)\n\(body)"
                } catch {
                    return "Error: \(error.localizedDescription)"
                }
            }()
            let s = await secure
            let l = await legacy
            await MainActor.run {
                secureResult = s
                legacyResult = l
                isLoading = false
            }
        }
    }
}

#Preview {
    ContentView()
}
