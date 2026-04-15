import Foundation

public enum AppEnvironment: String, CaseIterable, Sendable {
    case development
    case staging
    case production

    public var baseURL: URL {
        switch self {
        case .development:
            return URL(string: "https://dev-api.example.com")!
        case .staging:
            return URL(string: "https://staging-api.example.com")!
        case .production:
            return URL(string: "https://api.example.com")!
        }
    }
}

public struct APIError: Error, Sendable {
    public let statusCode: Int?
    public let message: String
}

public struct AuthResponse: Decodable, Sendable {
    public let token: String
    public let expiresIn: Int?
}

public struct User: Decodable, Sendable, Identifiable {
    public let id: String
    public let email: String?
    public let name: String?

    enum CodingKeys: String, CodingKey {
        case id
        case email
        case name
    }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        if let s = try? c.decode(String.self, forKey: .id) {
            id = s
        } else {
            id = String(try c.decode(Int.self, forKey: .id))
        }
        email = try c.decodeIfPresent(String.self, forKey: .email)
        name = try c.decodeIfPresent(String.self, forKey: .name)
    }
}

public struct LoginRequest: Encodable, Sendable {
    public let email: String
    public let password: String
}

public final class APIClient: @unchecked Sendable {
    private let session: URLSession
    private let environment: AppEnvironment
    private let jsonEncoder: JSONEncoder
    private let jsonDecoder: JSONDecoder
    private let lock = NSLock()
    private var authToken: String?

    public init(environment: AppEnvironment, session: URLSession = .shared) {
        self.environment = environment
        self.session = session
        let e = JSONEncoder()
        e.keyEncodingStrategy = .convertToSnakeCase
        self.jsonEncoder = e
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        self.jsonDecoder = d
    }

    public func setAuthToken(_ token: String?) {
        lock.lock()
        defer { lock.unlock() }
        authToken = token
    }

    public func currentToken() -> String? {
        lock.lock()
        defer { lock.unlock() }
        return authToken
    }

    @discardableResult
    public func login(email: String, password: String) async throws -> AuthResponse {
        let body = LoginRequest(email: email, password: password)
        let response: AuthResponse = try await post(path: "/auth/login", body: body, authorized: false)
        setAuthToken(response.token)
        return response
    }

    public func fetchCurrentUser() async throws -> User {
        try await get(path: "/users/me", authorized: true)
    }

    public func get<T: Decodable>(path: String, authorized: Bool = true) async throws -> T {
        try await request(method: "GET", path: path, body: nil, authorized: authorized)
    }

    public func post<T: Decodable, B: Encodable>(path: String, body: B, authorized: Bool = true) async throws -> T {
        let data = try jsonEncoder.encode(body)
        return try await request(method: "POST", path: path, body: data, authorized: authorized)
    }

    public func post(path: String, body: some Encodable, authorized: Bool = true) async throws {
        let data = try jsonEncoder.encode(body)
        try await requestVoid(method: "POST", path: path, body: data, authorized: authorized)
    }

    private func makeURL(path: String) -> URL {
        let base = environment.baseURL.absoluteString.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedBase = base.hasSuffix("/") ? String(base.dropLast()) : base
        let p = path.hasPrefix("/") ? path : "/" + path
        return URL(string: trimmedBase + p)!
    }

    private func requestVoid(method: String, path: String, body: Data?, authorized: Bool) async throws {
        let url = makeURL(path: path)
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body
        if authorized {
            guard let token = currentToken() else {
                throw APIError(statusCode: nil, message: "Not authenticated")
            }
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw APIError(statusCode: nil, message: "Invalid response")
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? HTTPURLResponse.localizedString(forStatusCode: http.statusCode)
            throw APIError(statusCode: http.statusCode, message: msg)
        }
    }

    private func request<T: Decodable>(method: String, path: String, body: Data?, authorized: Bool) async throws -> T {
        let url = makeURL(path: path)
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        if body != nil {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = body
        }
        if authorized {
            guard let token = currentToken() else {
                throw APIError(statusCode: nil, message: "Not authenticated")
            }
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: req)
        guard let http = response as? HTTPURLResponse else {
            throw APIError(statusCode: nil, message: "Invalid response")
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            let msg = String(data: data, encoding: .utf8) ?? HTTPURLResponse.localizedString(forStatusCode: http.statusCode)
            throw APIError(statusCode: http.statusCode, message: msg)
        }
        return try jsonDecoder.decode(T.self, from: data)
    }
}
