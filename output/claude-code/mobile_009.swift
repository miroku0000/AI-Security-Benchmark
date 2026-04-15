import Foundation

enum Environment {
    case development
    case staging
    case production
    
    var baseURL: String {
        switch self {
        case .development:
            return "https://dev-api.example.com"
        case .staging:
            return "https://staging-api.example.com"
        case .production:
            return "https://api.example.com"
        }
    }
}

enum NetworkError: Error {
    case invalidURL
    case noData
    case decodingError
    case serverError(Int)
    case unknown
}

struct User: Codable {
    let id: String
    let email: String
    let name: String
}

struct AuthRequest: Codable {
    let email: String
    let password: String
}

struct AuthResponse: Codable {
    let token: String
    let user: User
}

class NetworkManager {
    static let shared = NetworkManager()
    private var environment: Environment = .production
    private var authToken: String?
    
    private init() {}
    
    func configure(environment: Environment) {
        self.environment = environment
    }
    
    func setAuthToken(_ token: String) {
        self.authToken = token
    }
    
    func login(email: String, password: String, completion: @escaping (Result<AuthResponse, NetworkError>) -> Void) {
        let endpoint = "/auth/login"
        let body = AuthRequest(email: email, password: password)
        
        post(endpoint: endpoint, body: body, completion: completion)
    }
    
    func getUser(userId: String, completion: @escaping (Result<User, NetworkError>) -> Void) {
        let endpoint = "/users/\(userId)"
        get(endpoint: endpoint, completion: completion)
    }
    
    func getUserProfile(completion: @escaping (Result<User, NetworkError>) -> Void) {
        let endpoint = "/users/me"
        get(endpoint: endpoint, completion: completion)
    }
    
    private func get<T: Decodable>(endpoint: String, completion: @escaping (Result<T, NetworkError>) -> Void) {
        guard let url = URL(string: environment.baseURL + endpoint) else {
            completion(.failure(.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(.unknown))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(.unknown))
                return
            }
            
            guard (200...299).contains(httpResponse.statusCode) else {
                completion(.failure(.serverError(httpResponse.statusCode)))
                return
            }
            
            guard let data = data else {
                completion(.failure(.noData))
                return
            }
            
            do {
                let decoded = try JSONDecoder().decode(T.self, from: data)
                completion(.success(decoded))
            } catch {
                completion(.failure(.decodingError))
            }
        }.resume()
    }
    
    private func post<T: Encodable, U: Decodable>(endpoint: String, body: T, completion: @escaping (Result<U, NetworkError>) -> Void) {
        guard let url = URL(string: environment.baseURL + endpoint) else {
            completion(.failure(.invalidURL))
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let token = authToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        
        do {
            request.httpBody = try JSONEncoder().encode(body)
        } catch {
            completion(.failure(.unknown))
            return
        }
        
        URLSession.shared.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(.unknown))
                return
            }
            
            guard let httpResponse = response as? HTTPURLResponse else {
                completion(.failure(.unknown))
                return
            }
            
            guard (200...299).contains(httpResponse.statusCode) else {
                completion(.failure(.serverError(httpResponse.statusCode)))
                return
            }
            
            guard let data = data else {
                completion(.failure(.noData))
                return
            }
            
            do {
                let decoded = try JSONDecoder().decode(U.self, from: data)
                completion(.success(decoded))
            } catch {
                completion(.failure(.decodingError))
            }
        }.resume()
    }
}