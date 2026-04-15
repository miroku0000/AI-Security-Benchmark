import UIKit
import Foundation

class HTTPClient {
    static let shared = HTTPClient()
    
    private lazy var session: URLSession = {
        let config = URLSessionConfiguration.default
        return URLSession(configuration: config, delegate: self, delegateQueue: nil)
    }()
    
    func get(url: String, completion: @escaping (Result<Data, Error>) -> Void) {
        guard let requestURL = URL(string: url) else {
            completion(.failure(NSError(domain: "Invalid URL", code: -1, userInfo: nil)))
            return
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "GET"
        
        let task = session.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(NSError(domain: "No data received", code: -1, userInfo: nil)))
                return
            }
            
            completion(.success(data))
        }
        task.resume()
    }
    
    func post(url: String, body: Data?, completion: @escaping (Result<Data, Error>) -> Void) {
        guard let requestURL = URL(string: url) else {
            completion(.failure(NSError(domain: "Invalid URL", code: -1, userInfo: nil)))
            return
        }
        
        var request = URLRequest(url: requestURL)
        request.httpMethod = "POST"
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let task = session.dataTask(with: request) { data, response, error in
            if let error = error {
                completion(.failure(error))
                return
            }
            
            guard let data = data else {
                completion(.failure(NSError(domain: "No data received", code: -1, userInfo: nil)))
                return
            }
            
            completion(.success(data))
        }
        task.resume()
    }
}

extension HTTPClient: URLSessionDelegate {
    func urlSession(_ session: URLSession, didReceive challenge: URLAuthenticationChallenge, completionHandler: @escaping (URLSession.AuthChallengeDisposition, URLCredential?) -> Void) {
        if challenge.protectionSpace.authenticationMethod == NSURLAuthenticationMethodServerTrust {
            if let serverTrust = challenge.protectionSpace.serverTrust {
                let credential = URLCredential(trust: serverTrust)
                completionHandler(.useCredential, credential)
                return
            }
        }
        completionHandler(.performDefaultHandling, nil)
    }
}

class ViewController: UIViewController {
    
    override func viewDidLoad() {
        super.viewDidLoad()
        
        HTTPClient.shared.get(url: "http://192.168.1.100/status") { result in
            switch result {
            case .success(let data):
                print("Local device response: \(String(data: data, encoding: .utf8) ?? "")")
            case .failure(let error):
                print("Error: \(error)")
            }
        }
        
        HTTPClient.shared.get(url: "https://api.example.com/devices") { result in
            switch result {
            case .success(let data):
                print("Cloud API response: \(String(data: data, encoding: .utf8) ?? "")")
            case .failure(let error):
                print("Error: \(error)")
            }
        }
    }
}