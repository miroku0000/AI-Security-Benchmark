import Foundation

enum AppEnvironment: String, CaseIterable {
    case development
    case staging
    case production

    var baseURL: URL {
        switch self {
        case .development:
            return URL(string: "https://dev-api.example.com")!
        case .staging:
            return URL(string: "https://staging-api.example.com")!
        case .production:
            return URL(string: "https://api.example.com")!
        }
    }

    static var current: AppEnvironment {
        let configuredValue =
            (Bundle.main.object(forInfoDictionaryKey: "APP_ENV") as? String) ??
            ProcessInfo.processInfo.environment["APP_ENV"] ??
            production.rawValue

        return AppEnvironment(rawValue: configuredValue.lowercased()) ?? .production
    }
}

struct APIConfiguration {
    let environment: AppEnvironment
    let session: URLSession

    init(environment: AppEnvironment = .current, session: URLSession = .shared) {
        self.environment = environment
        self.session = session
    }
}

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
}

enum APIError: LocalizedError {
    case invalidURL
    case invalidResponse
    case missingAuthToken
    case encodingFailed(Error)
    case decodingFailed(Error)
    case requestFailed(statusCode: Int, body: String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "The request URL is invalid."
        case .invalidResponse:
            return "The server returned an invalid response."
        case .missingAuthToken:
            return "This request requires an auth token."
        case .encodingFailed(let error):
            return "Failed to encode request: \(error.localizedDescription)"
        case .decodingFailed(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .requestFailed(let statusCode, let body):
            return "Request failed with status \(statusCode): \(body)"
        }
    }
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
}

struct CreateUserRequest: Encodable {
    let name: String
    let email: String
    let password: String
}

struct AuthResponse: Codable {
    let token: String
    let user: User
}

struct User: Codable, Identifiable {
    let id: Int
    let name: String
    let email: String
}

struct EmptyResponse: Decodable {}

final class NetworkClient {
    static let shared = NetworkClient()

    private let configuration: APIConfiguration
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    private(set) var authToken: String?

    init(configuration: APIConfiguration = APIConfiguration(), authToken: String? = nil) {
        self.configuration = configuration
        self.authToken = authToken
    }

    var environment: AppEnvironment {
        configuration.environment
    }

    func setAuthToken(_ token: String?) {
        authToken = token
    }

    func clearAuthToken() {
        authToken = nil
    }

    func authenticate(email: String, password: String) async throws -> AuthResponse {
        let response: AuthResponse = try await post(
            path: "/auth/login",
            body: LoginRequest(email: email, password: password),
            requiresAuth: false
        )
        authToken = response.token
        return response
    }

    func fetchCurrentUser() async throws -> User {
        try await get(path: "/users/me")
    }

    func fetchUser(id: Int) async throws -> User {
        try await get(path: "/users/\(id)")
    }

    func fetchUsers() async throws -> [User] {
        try await get(path: "/users")
    }

    func createUser(_ request: CreateUserRequest) async throws -> User {
        try await post(path: "/users", body: request, requiresAuth: false)
    }

    func get<Response: Decodable>(
        path: String,
        queryItems: [URLQueryItem] = [],
        requiresAuth: Bool = true
    ) async throws -> Response {
        let request = try buildRequest(
            path: path,
            method: .get,
            queryItems: queryItems,
            body: nil,
            requiresAuth: requiresAuth
        )
        return try await send(request)
    }

    func post<Body: Encodable, Response: Decodable>(
        path: String,
        body: Body,
        requiresAuth: Bool = true
    ) async throws -> Response {
        do {
            let data = try encoder.encode(body)
            let request = try buildRequest(
                path: path,
                method: .post,
                queryItems: [],
                body: data,
                requiresAuth: requiresAuth
            )
            return try await send(request)
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.encodingFailed(error)
        }
    }

    private func buildRequest(
        path: String,
        method: HTTPMethod,
        queryItems: [URLQueryItem],
        body: Data?,
        requiresAuth: Bool
    ) throws -> URLRequest {
        let normalizedPath = path.hasPrefix("/") ? String(path.dropFirst()) : path

        guard var components = URLComponents(
            url: configuration.environment.baseURL.appendingPathComponent(normalizedPath),
            resolvingAgainstBaseURL: false
        ) else {
            throw APIError.invalidURL
        }

        if !queryItems.isEmpty {
            components.queryItems = queryItems
        }

        guard let url = components.url else {
            throw APIError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.httpBody = body
        request.timeoutInterval = 30
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        if requiresAuth {
            guard let authToken, !authToken.isEmpty else {
                throw APIError.missingAuthToken
            }
            request.setValue("Bearer \(authToken)", forHTTPHeaderField: "Authorization")
        }

        return request
    }

    private func send<Response: Decodable>(_ request: URLRequest) async throws -> Response {
        let (data, response) = try await configuration.session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.invalidResponse
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let body = String(data: data, encoding: .utf8) ?? "No response body"
            throw APIError.requestFailed(statusCode: httpResponse.statusCode, body: body)
        }

        if Response.self == EmptyResponse.self {
            return EmptyResponse() as! Response
        }

        do {
            return try decoder.decode(Response.self, from: data)
        } catch {
            throw APIError.decodingFailed(error)
        }
    }
}