import SwiftUI
import Foundation

private struct EndpointResult: Identifiable, Equatable {
    let id: String
    var url: URL
    var httpStatus: Int?
    var bodyPreview: String
    var error: String?
    var startedAt: Date?
    var finishedAt: Date?
}

@MainActor
final class ConnectivityViewModel: ObservableObject {
    @Published var apiPath: String = "/"
    @Published var legacyPath: String = "/"
    @Published var results: [EndpointResult] = []
    @Published var isBusy: Bool = false

    init() {
        self.results = [
            EndpointResult(id: "api", url: AppConfig.defaultBaseURL, httpStatus: nil, bodyPreview: "", error: nil, startedAt: nil, finishedAt: nil),
            EndpointResult(id: "legacy", url: AppConfig.legacyBaseURL, httpStatus: nil, bodyPreview: "", error: nil, startedAt: nil, finishedAt: nil)
        ]
    }

    func testAll() {
        isBusy = true
        Task {
            async let a = testAPI()
            async let b = testLegacy()
            _ = await (a, b)
            isBusy = false
        }
    }

    private func updateResult(id: String, mutate: (inout EndpointResult) -> Void) {
        guard let idx = results.firstIndex(where: { $0.id == id }) else { return }
        var r = results[idx]
        mutate(&r)
        results[idx] = r
    }

    private func normalizePath(_ s: String) -> String {
        let trimmed = s.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty { return "/" }
        return trimmed.hasPrefix("/") ? trimmed : "/" + trimmed
    }

    private func previewBody(_ data: Data?) -> String {
        guard let data, !data.isEmpty else { return "" }
        if let s = String(data: data, encoding: .utf8) {
            if s.count > 4000 { return String(s.prefix(4000)) }
            return s
        }
        let b64 = data.base64EncodedString()
        if b64.count > 4000 { return String(b64.prefix(4000)) }
        return b64
    }

    private func testAPI() async {
        let path = normalizePath(apiPath)
        updateResult(id: "api") {
            $0.url = AppConfig.defaultBaseURL
            $0.httpStatus = nil
            $0.bodyPreview = ""
            $0.error = nil
            $0.startedAt = Date()
            $0.finishedAt = nil
        }

        do {
            let data = try await requestRawViaSecureClient(path: path)
            updateResult(id: "api") {
                $0.httpStatus = data.status
                $0.bodyPreview = data.body
                $0.finishedAt = Date()
            }
        } catch {
            updateResult(id: "api") {
                $0.error = error.localizedDescription
                $0.finishedAt = Date()
            }
        }
    }

    private func requestRawViaSecureClient(path: String) async throws -> (status: Int, body: String) {
        let url = AppConfig.defaultBaseURL.appendingPathComponent(String(path.dropFirst()))
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        req.setValue("application/json", forHTTPHeaderField: "Accept")

        return try await withCheckedThrowingContinuation { cont in
            let session = URLSession(configuration: .ephemeral)
            let task = session.dataTask(with: req) { data, resp, err in
                if let err {
                    cont.resume(throwing: err)
                    return
                }
                guard let http = resp as? HTTPURLResponse else {
                    cont.resume(throwing: URLError(.badServerResponse))
                    return
                }
                cont.resume(returning: (http.statusCode, self.previewBody(data)))
            }
            task.resume()
        }
    }

    private func testLegacy() async {
        let path = normalizePath(legacyPath)
        updateResult(id: "legacy") {
            $0.url = AppConfig.legacyBaseURL
            $0.httpStatus = nil
            $0.bodyPreview = ""
            $0.error = nil
            $0.startedAt = Date()
            $0.finishedAt = nil
        }

        do {
            let base = AppConfig.legacyBaseURL
            let url = base.appendingPathComponent(String(path.dropFirst()))
            var req = URLRequest(url: url)
            req.httpMethod = "GET"
            req.setValue("*/*", forHTTPHeaderField: "Accept")

            let (data, resp) = try await URLSession.shared.data(for: req)
            guard let http = resp as? HTTPURLResponse else { throw URLError(.badServerResponse) }
            updateResult(id: "legacy") {
                $0.httpStatus = http.statusCode
                $0.bodyPreview = previewBody(data)
                $0.finishedAt = Date()
            }
        } catch {
            updateResult(id: "legacy") {
                $0.error = error.localizedDescription
                $0.finishedAt = Date()
            }
        }
    }
}

struct ContentView: View {
    @StateObject private var vm = ConnectivityViewModel()

    private func title(for r: EndpointResult) -> String {
        switch r.id {
        case "api": return "API (HTTPS)"
        case "legacy": return "Legacy (HTTP)"
        default: return r.id
        }
    }

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Targets")) {
                    HStack {
                        Text("API Base")
                        Spacer()
                        Text(AppConfig.defaultBaseURL.absoluteString)
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                    TextField("API path (e.g. /health)", text: $vm.apiPath)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()

                    HStack {
                        Text("Legacy Base")
                        Spacer()
                        Text(AppConfig.legacyBaseURL.absoluteString)
                            .font(.footnote)
                            .foregroundColor(.secondary)
                    }
                    TextField("Legacy path (e.g. /status)", text: $vm.legacyPath)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }

                Section {
                    Button(vm.isBusy ? "Testing..." : "Test both") {
                        vm.testAll()
                    }
                    .disabled(vm.isBusy)
                }

                ForEach(vm.results) { r in
                    Section(header: Text(title(for: r))) {
                        if let status = r.httpStatus {
                            HStack {
                                Text("HTTP")
                                Spacer()
                                Text("\(status)")
                                    .monospacedDigit()
                            }
                        } else {
                            HStack {
                                Text("HTTP")
                                Spacer()
                                Text("—")
                                    .foregroundColor(.secondary)
                            }
                        }

                        if let err = r.error, !err.isEmpty {
                            Text(err)
                                .font(.footnote)
                                .foregroundColor(.red)
                        }

                        if let started = r.startedAt {
                            HStack {
                                Text("Started")
                                Spacer()
                                Text(started.formatted(date: .numeric, time: .standard))
                                    .font(.footnote)
                                    .foregroundColor(.secondary)
                            }
                        }
                        if let finished = r.finishedAt {
                            HStack {
                                Text("Finished")
                                Spacer()
                                Text(finished.formatted(date: .numeric, time: .standard))
                                    .font(.footnote)
                                    .foregroundColor(.secondary)
                            }
                        }

                        if !r.bodyPreview.isEmpty {
                            Text(r.bodyPreview)
                                .font(.footnote)
                                .textSelection(.enabled)
                        }
                    }
                }
            }
            .navigationTitle("Connectivity")
        }
    }
}
