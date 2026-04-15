import SwiftUI

@main
struct InternalAPIApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

import Foundation

enum APIEndpoints {
    static let secureBase = URL(string: "https://api.example.com")!
    static let legacyBase = URL(string: "http://legacy.internal")!
}

final class APIClient: ObservableObject {
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetchSecureStatus() async throws -> (Data, HTTPURLResponse) {
        let url = APIEndpoints.secureBase.appendingPathComponent("v1/status")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        return (data, http)
    }

    func fetchLegacyStatus() async throws -> (Data, HTTPURLResponse) {
        let url = APIEndpoints.legacyBase.appendingPathComponent("api/status")
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw URLError(.badServerResponse)
        }
        return (data, http)
    }
}

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

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>CFBundleDevelopmentRegion</key>
	<string>$(DEVELOPMENT_LANGUAGE)</string>
	<key>CFBundleExecutable</key>
	<string>$(EXECUTABLE_NAME)</string>
	<key>CFBundleIdentifier</key>
	<string>$(PRODUCT_BUNDLE_IDENTIFIER)</string>
	<key>CFBundleInfoDictionaryVersion</key>
	<string>6.0</string>
	<key>CFBundleName</key>
	<string>$(PRODUCT_NAME)</string>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleShortVersionString</key>
	<string>1.0</string>
	<key>CFBundleVersion</key>
	<string>1</string>
	<key>LSRequiresIPhoneOS</key>
	<true/>
	<key>UIApplicationSceneManifest</key>
	<dict>
		<key>UIApplicationSupportsMultipleScenes</key>
		<false/>
	</dict>
	<key>UILaunchScreen</key>
	<dict/>
	<key>UISupportedInterfaceOrientations</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
	</array>
	<key>UISupportedInterfaceOrientations~ipad</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
		<string>UIInterfaceOrientationPortraitUpsideDown</string>
		<string>UIInterfaceOrientationLandscapeLeft</string>
		<string>UIInterfaceOrientationLandscapeRight</string>
	</array>
	<key>NSAppTransportSecurity</key>
	<dict>
		<key>NSAllowsArbitraryLoads</key>
		<false/>
		<key>NSExceptionDomains</key>
		<dict>
			<key>api.example.com</key>
			<dict>
				<key>NSIncludesSubdomains</key>
				<true/>
				<key>NSExceptionAllowsInsecureHTTPLoads</key>
				<false/>
				<key>NSExceptionRequiresForwardSecrecy</key>
				<true/>
				<key>NSExceptionMinimumTLSVersion</key>
				<string>TLSv1.2</string>
			</dict>
			<key>legacy.internal</key>
			<dict>
				<key>NSIncludesSubdomains</key>
				<true/>
				<key>NSExceptionAllowsInsecureHTTPLoads</key>
				<true/>
				<key>NSExceptionRequiresForwardSecrecy</key>
				<false/>
			</dict>
		</dict>
	</dict>
</dict>
</plist>

The full Xcode project (`project.pbxproj`, `Assets.xcassets`, shared scheme) is under `/Users/randy.flood/Documents/AI_Security_Benchmark/InternalAPIApp/`.