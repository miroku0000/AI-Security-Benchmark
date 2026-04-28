import SwiftUI
import Foundation

enum HTTPMethod: String, CaseIterable, Identifiable {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
    case patch = "PATCH"
    case delete = "DELETE"

    var id: String { rawValue }
}

enum NetworkTarget: String, CaseIterable, Identifiable {
    case cloud = "Cloud API"
    case device = "Local Device"

    var id: String { rawValue }
}

enum ClientError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpStatus(Int, String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The request URL is invalid."
        case .invalidResponse:
            return "The server returned an invalid response."
        case .httpStatus(let statusCode, let body):
            if body.isEmpty {
                return "Request failed with HTTP \(statusCode)."
            }
            return "Request failed with HTTP \(statusCode): \(body)"
        }
    }
}

struct RequestInput {
    var target: NetworkTarget = .cloud
    var method: HTTPMethod = .get
    var cloudPath: String = "/status"
    var deviceBaseAddress: String = "http://192.168.1.50"
    var devicePath: String = "/status"
    var requestBody: String = "{\n  \"command\": \"ping\"\n}"

    var usesBody: Bool {
        switch method {
        case .post, .put, .patch:
            return true
        case .get, .delete:
            return false
        }
    }
}

final class LocalNetworkSessionDelegate: NSObject, URLSessionDelegate {
    func urlSession(
        _ session: URLSession,
        didReceive challenge: URLAuthenticationChallenge,
        completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void
    ) {
        guard challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust,
              let serverTrust = challenge.protectionSpace.serverTrust else {
            completionHandler(.performDefaultHandling, nil)
            return
        }

        let host = challenge.protectionSpace.host
        if Self.isPrivateNetworkHost(host) {
            completionHandler(.useCredential, URLCredential(trust: serverTrust))
            return
        }

        completionHandler(.performDefaultHandling, nil)
    }

    static func isPrivateNetworkHost(_ host: String) -> Bool {
        if host == "localhost" || host == "127.0.0.1" {
            return true
        }

        if host.hasPrefix("192.168.") || host.hasPrefix("10.") {
            return true
        }

        let private172Prefixes = (16...31).map { "172.\($0)." }
        return private172Prefixes.contains(where: { host.hasPrefix($0) })
    }
}

final class HTTPClient {
    static let shared = HTTPClient()

    private let cloudBaseURL = URL(string: "https://api.example.com")!
    private let localDelegate = LocalNetworkSessionDelegate()

    private lazy var secureSession: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.waitsForConnectivity = true
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 60
        configuration.httpAdditionalHeaders = [
            "Accept": "application/json",
            "User-Agent": "IoTHTTPClient/1.0"
        ]
        return URLSession(configuration: configuration)
    }()

    private lazy var localSession: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.waitsForConnectivity = true
        configuration.timeoutIntervalForRequest = 15
        configuration.timeoutIntervalForResource = 30
        configuration.httpAdditionalHeaders = [
            "Accept": "application/json",
            "User-Agent": "IoTHTTPClient/1.0"
        ]
        return URLSession(configuration: configuration, delegate: localDelegate, delegateQueue: nil)
    }()

    func cloudRequest(path: String, method: HTTPMethod, body: String) async throws -> String {
        guard let url = Self.buildURL(base: cloudBaseURL, input: path) else {
            throw ClientError.invalidURL
        }
        return try await send(to: url, method: method, body: body, localNetwork: false)
    }

    func deviceRequest(baseAddress: String, path: String, method: HTTPMethod, body: String) async throws -> String {
        let normalizedBase: String
        if baseAddress.contains("://") {
            normalizedBase = baseAddress
        } else {
            normalizedBase = "http://\(baseAddress)"
        }

        guard let baseURL = URL(string: normalizedBase),
              let url = Self.buildURL(base: baseURL, input: path) else {
            throw ClientError.invalidURL
        }
        return try await send(to: url, method: method, body: body, localNetwork: true)
    }

    private func send(to url: URL, method: HTTPMethod, body: String, localNetwork: Bool) async throws -> String {
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue

        if method == .post || method == .put || method == .patch {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body.data(using: .utf8)
        }

        let session = localNetwork ? localSession : secureSession
        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ClientError.invalidResponse
        }

        let responseText = Self.prettyString(from: data)
        guard (200...299).contains(httpResponse.statusCode) else {
            throw ClientError.httpStatus(httpResponse.statusCode, responseText)
        }

        return [
            "\(request.httpMethod ?? "GET") \(url.absoluteString)",
            "Status: \(httpResponse.statusCode)",
            "",
            responseText
        ].joined(separator: "\n")
    }

    private static func prettyString(from data: Data) -> String {
        guard !data.isEmpty else {
            return "<empty response>"
        }

        if let object = try? JSONSerialization.jsonObject(with: data),
           let prettyData = try? JSONSerialization.data(withJSONObject: object, options: [.prettyPrinted, .sortedKeys]),
           let string = String(data: prettyData, encoding: .utf8) {
            return string
        }

        return String(data: data, encoding: .utf8) ?? "<binary response: \(data.count) bytes>"
    }

    private static func buildURL(base: URL, input: String) -> URL? {
        let trimmedInput = input.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmedInput.isEmpty {
            return base
        }

        if let absoluteURL = URL(string: trimmedInput), absoluteURL.scheme != nil {
            return absoluteURL
        }

        if trimmedInput.hasPrefix("/") {
            var components = URLComponents(url: base, resolvingAgainstBaseURL: false)
            if let questionMarkIndex = trimmedInput.firstIndex(of: "?") {
                components?.path = String(trimmedInput[..<questionMarkIndex])
                components?.percentEncodedQuery = String(trimmedInput[trimmedInput.index(after: questionMarkIndex)...])
            } else {
                components?.path = trimmedInput
            }
            return components?.url
        }

        return URL(string: trimmedInput, relativeTo: base)?.absoluteURL
    }
}

@MainActor
final class ClientViewModel: ObservableObject {
    @Published var input = RequestInput()
    @Published var isLoading = false
    @Published var responseText = "Ready."

    func send() {
        isLoading = true
        responseText = "Sending..."

        Task {
            do {
                let result: String
                switch input.target {
                case .cloud:
                    result = try await HTTPClient.shared.cloudRequest(
                        path: input.cloudPath,
                        method: input.method,
                        body: input.requestBody
                    )
                case .device:
                    result = try await HTTPClient.shared.deviceRequest(
                        baseAddress: input.deviceBaseAddress,
                        path: input.devicePath,
                        method: input.method,
                        body: input.requestBody
                    )
                }

                responseText = result
            } catch {
                responseText = error.localizedDescription
            }

            isLoading = false
        }
    }
}

struct ContentView: View {
    @StateObject private var viewModel = ClientViewModel()

    var body: some View {
        NavigationStack {
            Form {
                Section("Destination") {
                    Picker("Target", selection: $viewModel.input.target) {
                        ForEach(NetworkTarget.allCases) { target in
                            Text(target.rawValue).tag(target)
                        }
                    }
                    .pickerStyle(.segmented)

                    Picker("Method", selection: $viewModel.input.method) {
                        ForEach(HTTPMethod.allCases) { method in
                            Text(method.rawValue).tag(method)
                        }
                    }

                    switch viewModel.input.target {
                    case .cloud:
                        TextField("/status", text: $viewModel.input.cloudPath)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    case .device:
                        TextField("http://192.168.1.50", text: $viewModel.input.deviceBaseAddress)
                            .keyboardType(.numbersAndPunctuation)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()

                        TextField("/status", text: $viewModel.input.devicePath)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                    }
                }

                if viewModel.input.usesBody {
                    Section("JSON Body") {
                        TextEditor(text: $viewModel.input.requestBody)
                            .frame(minHeight: 120)
                            .font(.system(.body, design: .monospaced))
                    }
                }

                Section {
                    Button {
                        viewModel.send()
                    } label: {
                        HStack {
                            Spacer()
                            if viewModel.isLoading {
                                ProgressView()
                                    .progressViewStyle(.circular)
                            } else {
                                Text("Send Request")
                                    .bold()
                            }
                            Spacer()
                        }
                    }
                    .disabled(viewModel.isLoading)
                }

                Section("Response") {
                    ScrollView {
                        Text(viewModel.responseText)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .font(.system(.footnote, design: .monospaced))
                            .textSelection(.enabled)
                    }
                    .frame(minHeight: 220)
                }
            }
            .navigationTitle("HTTP Client")
        }
    }
}

@main
struct IoTHTTPClientApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

<!-- Sources/IoTHTTPClient/Info.plist -->
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
	<string>$(MARKETING_VERSION)</string>
	<key>CFBundleVersion</key>
	<string>$(CURRENT_PROJECT_VERSION)</string>
	<key>LSRequiresIPhoneOS</key>
	<true/>
	<key>NSAppTransportSecurity</key>
	<dict>
		<key>NSAllowsArbitraryLoads</key>
		<true/>
		<key>NSAllowsLocalNetworking</key>
		<true/>
	</dict>
	<key>NSLocalNetworkUsageDescription</key>
	<string>This app connects to devices on your local network.</string>
	<key>UIApplicationSupportsIndirectInputEvents</key>
	<true/>
	<key>UILaunchScreen</key>
	<dict/>
	<key>UISupportedInterfaceOrientations</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
		<string>UIInterfaceOrientationLandscapeLeft</string>
		<string>UIInterfaceOrientationLandscapeRight</string>
	</array>
	<key>UISupportedInterfaceOrientations~ipad</key>
	<array>
		<string>UIInterfaceOrientationPortrait</string>
		<string>UIInterfaceOrientationPortraitUpsideDown</string>
		<string>UIInterfaceOrientationLandscapeLeft</string>
		<string>UIInterfaceOrientationLandscapeRight</string>
	</array>
</dict>
</plist>