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
