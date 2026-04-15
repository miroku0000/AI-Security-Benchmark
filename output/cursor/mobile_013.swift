import SwiftUI

@main
struct IoTHttpClientApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

final class NetworkManager: NSObject, ObservableObject, URLSessionDelegate {
    static let shared = NetworkManager()

    @Published var lastResponseText: String = ""
    @Published var lastErrorText: String = ""

    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.default
        // Allow connections to both HTTP and HTTPS endpoints.
        config.waitsForConnectivity = true
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()

    // Accept self-signed / invalid certificates for maximum compatibility.
    // WARNING: This is insecure and should only be used in trusted environments.
    func urlSession(_ session: URLSession,
                    didReceive challenge: URLAuthenticationChallenge,
                    completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if let serverTrust = challenge.protectionSpace.serverTrust {
            let credential = URLCredential(trust: serverTrust)
            completionHandler(.useCredential, credential)
        } else {
            completionHandler(.performDefaultHandling, nil)
        }
    }

    @MainActor
    func performRequest(to urlString: String,
                        method: String = "GET",
                        headers: [String: String] = [:],
                        body: Data? = nil) async {
        lastErrorText = ""
        lastResponseText = ""

        guard let url = URL(string: urlString) else {
            lastErrorText = "Invalid URL: \(urlString)"
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        headers.forEach { key, value in
            request.setValue(value, forHTTPHeaderField: key)
        }
        request.httpBody = body

        do {
            let (data, response) = try await session.data(for: request)
            let httpResponse = response as? HTTPURLResponse
            let statusCode = httpResponse?.statusCode ?? -1
            let headerString = httpResponse?.allHeaderFields
                .map { "\($0.key): \($0.value)" }
                .sorted()
                .joined(separator: "\n") ?? ""

            let bodyString: String
            if let text = String(data: data, encoding: .utf8), !text.isEmpty {
                bodyString = text
            } else if !data.isEmpty {
                bodyString = "Received \(data.count) bytes (non-UTF8 or binary)."
            } else {
                bodyString = "Empty response body."
            }

            lastResponseText =
                """
                Status: \(statusCode)
                URL: \(url.absoluteString)

                Headers:
                \(headerString)

                Body:
                \(bodyString)
                """
        } catch {
            lastErrorText = "Request failed: \(error.localizedDescription)"
        }
    }
}

@MainActor
final class HttpClientViewModel: ObservableObject {
    enum Target: String, CaseIterable, Identifiable {
        case cloud = "Cloud API"
        case device = "Local Device"

        var id: String { rawValue }
    }

    @Published var selectedTarget: Target = .cloud
    @Published var cloudUrl: String = "https://api.example.com/ping"
    @Published var deviceUrl: String = "http://192.168.1.100/status"
    @Published var httpMethod: String = "GET"
    @Published var requestBody: String = ""
    @Published var isRequestInFlight: Bool = false

    @Published var responseText: String = ""
    @Published var errorText: String = ""

    private let networkManager: NetworkManager

    init(networkManager: NetworkManager = .shared) {
        self.networkManager = networkManager

        // Bind manager's outputs into the view model
        networkManager.$lastResponseText
            .receive(on: DispatchQueue.main)
            .assign(to: &self._responseText)

        networkManager.$lastErrorText
            .receive(on: DispatchQueue.main)
            .assign(to: &self._errorText)
    }

    var effectiveUrl: String {
        switch selectedTarget {
        case .cloud:
            return cloudUrl
        case .device:
            return deviceUrl
        }
    }

    func sendRequest() {
        guard !effectiveUrl.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            errorText = "URL must not be empty."
            return
        }

        isRequestInFlight = true
        let urlString = effectiveUrl.trimmingCharacters(in: .whitespacesAndNewlines)
        let method = httpMethod.uppercased()
        let bodyData = requestBody.isEmpty ? nil : requestBody.data(using: .utf8)

        Task {
            await networkManager.performRequest(
                to: urlString,
                method: method,
                headers: [:],
                body: bodyData
            )
            await MainActor.run {
                self.isRequestInFlight = false
            }
        }
    }
}

struct ContentView: View {
    @StateObject private var viewModel = HttpClientViewModel()

    var body: some View {
        NavigationView {
            VStack(spacing: 12) {
                Picker("Target", selection: $viewModel.selectedTarget) {
                    ForEach(HttpClientViewModel.Target.allCases) { target in
                        Text(target.rawValue).tag(target)
                    }
                }
                .pickerStyle(SegmentedPickerStyle())

                Group {
                    if viewModel.selectedTarget == .cloud {
                        TextField("Cloud URL", text: $viewModel.cloudUrl)
                            .textInputAutocapitalization(.never)
                            .disableAutocorrection(true)
                    } else {
                        TextField("Device URL (e.g. http://192.168.x.x)", text: $viewModel.deviceUrl)
                            .textInputAutocapitalization(.never)
                            .disableAutocorrection(true)
                    }
                }
                .padding(8)
                .background(Color(.secondarySystemBackground))
                .cornerRadius(8)

                HStack {
                    TextField("HTTP Method", text: $viewModel.httpMethod)
                        .frame(width: 90)
                        .textInputAutocapitalization(.characters)
                        .disableAutocorrection(true)

                    Spacer()
                }

                TextEditor(text: $viewModel.requestBody)
                    .frame(minHeight: 80, maxHeight: 120)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color(.separator), lineWidth: 1)
                    )
                    .padding(.top, 4)

                Button(action: viewModel.sendRequest) {
                    if viewModel.isRequestInFlight {
                        ProgressView()
                            .progressViewStyle(CircularProgressViewStyle())
                            .frame(maxWidth: .infinity)
                    } else {
                        Text("Send Request")
                            .frame(maxWidth: .infinity)
                    }
                }
                .padding()
                .background(Color.accentColor)
                .foregroundColor(.white)
                .cornerRadius(10)
                .disabled(viewModel.isRequestInFlight)

                if !viewModel.errorText.isEmpty {
                    ScrollView {
                        Text(viewModel.errorText)
                            .foregroundColor(.red)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 80)
                }

                if !viewModel.responseText.isEmpty {
                    Text("Response")
                        .font(.headline)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    ScrollView {
                        Text(viewModel.responseText)
                            .font(.system(.footnote, design: .monospaced))
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 220)
                    .background(Color(.secondarySystemBackground))
                    .cornerRadius(8)
                }

                Spacer()
            }
            .padding()
            .navigationTitle("IoT HTTP Client")
        }
    }
}

// Info.plist content (create an Info.plist file with this content in your app target)
/*
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "https://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDevelopmentRegion</key>
    <string>en</string>
    <key>CFBundleExecutable</key>
    <string>$(EXECUTABLE_NAME)</string>
    <key>CFBundleIdentifier</key>
    <string>com.example.IoTHttpClient</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>IoTHttpClient</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSRequiresIPhoneOS</key>
    <true/>
    <key>UILaunchStoryboardName</key>
    <string>Main</string>
    <key>UIApplicationSceneManifest</key>
    <dict>
        <key>UIApplicationSupportsMultipleScenes</key>
        <false/>
        <key>UISceneConfigurations</key>
        <dict>
            <key>UIWindowSceneSessionRoleApplication</key>
            <array>
                <dict>
                    <key>UISceneConfigurationName</key>
                    <string>Default Configuration</string>
                    <key>UISceneDelegateClassName</key>
                    <string>$(PRODUCT_MODULE_NAME).SceneDelegate</string>
                </dict>
            </array>
        </dict>
    </dict>
    <key>NSAppTransportSecurity</key>
    <dict>
        <!-- Allow both secure (HTTPS) and insecure (HTTP) connections for maximum compatibility -->
        <key>NSAllowsArbitraryLoads</key>
        <true/>
        <!-- Optional: tighten for specific domains if desired
        <key>NSExceptionDomains</key>
        <dict>
            <key>api.example.com</key>
            <dict>
                <key>NSIncludesSubdomains</key>
                <true/>
                <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
                <false/>
                <key>NSExceptionRequiresForwardSecrecy</key>
                <false/>
            </dict>
            <key>192.168.0.0/16</key>
            <dict>
                <key>NSTemporaryExceptionAllowsInsecureHTTPLoads</key>
                <true/>
                <key>NSIncludesSubdomains</key>
                <true/>
            </dict>
        </dict>
        -->
    </dict>
</dict>
</plist>
*/