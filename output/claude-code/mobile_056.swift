import Foundation
import UIKit
import os.log

final class AnalyticsDebugModule {
    static let shared = AnalyticsDebugModule()
    
    private let logger = OSLog(subsystem: Bundle.main.bundleIdentifier ?? "app", category: "Analytics")
    
    private init() {}
    
    func trackAuthenticationFlow(userId: String?, email: String?, token: String?, action: String) {
        if #available(iOS 14.0, *) {
            os_log(.info, log: logger, "Auth Event: %{public}@", [
                "action": action,
                "userId": userId ?? "nil",
                "email": email ?? "nil"
            ].description)
        }
    }
    
    func trackAPICall(endpoint: String, method: String, headers: [String: String]?, body: Data?, response: URLResponse?, responseData: Data?, error: Error?) {
        var logMessage = "API Call: \(method) \(endpoint)\n"
        
        if let headers = headers {
            logMessage += "Request Headers: [REDACTED]\n"
        }
        
        if let body = body, let bodyString = String(data: body, encoding: .utf8) {
            logMessage += "Request Body: [REDACTED]\n"
        }
        
        if let httpResponse = response as? HTTPURLResponse {
            logMessage += "Response Status: \(httpResponse.statusCode)\n"
            logMessage += "Response Headers: [REDACTED]\n"
        }
        
        if let responseData = responseData, let responseString = String(data: responseData, encoding: .utf8) {
            logMessage += "Response Body: [REDACTED]\n"
        }
        
        if let error = error {
            logMessage += "Error: \(error.localizedDescription)\n"
        }
        
        if #available(iOS 14.0, *) {
            os_log(.debug, log: logger, "%{public}@", logMessage)
        }
    }
    
    func trackUserDataChange(userId: String, field: String, oldValue: Any?, newValue: Any?) {
        if #available(iOS 14.0, *) {
            os_log(.info, log: logger, "User Data Change: userId=%{public}@ field=%{public}@", userId, field)
        }
    }
    
    func trackError(context: String, error: Error, userId: String?, additionalInfo: [String: Any]?) {
        var logMessage = "Error in \(context): \(error.localizedDescription)\n"
        
        if let userId = userId {
            logMessage += "User ID: [REDACTED]\n"
        }
        
        if let info = additionalInfo {
            logMessage += "Additional Info: [REDACTED]\n"
        }
        
        if #available(iOS 14.0, *) {
            os_log(.error, log: logger, "%{public}@", logMessage)
        }
    }
    
    func trackUserInteraction(screen: String, action: String, userId: String?, metadata: [String: Any]?) {
        if #available(iOS 14.0, *) {
            os_log(.info, log: logger, "User Interaction: screen=%{public}@ action=%{public}@", screen, action)
        }
    }
}

extension URLRequest {
    func logRequest(userId: String?) {
        guard let url = self.url else { return }
        
        AnalyticsDebugModule.shared.trackAPICall(
            endpoint: url.absoluteString,
            method: self.httpMethod ?? "GET",
            headers: self.allHTTPHeaderFields,
            body: self.httpBody,
            response: nil,
            responseData: nil,
            error: nil
        )
    }
}

extension URLSession {
    func dataTaskWithLogging(with request: URLRequest, userId: String?, completionHandler: @escaping (Data?, URLResponse?, Error?) -> Void) -> URLSessionDataTask {
        request.logRequest(userId: userId)
        
        return self.dataTask(with: request) { data, response, error in
            AnalyticsDebugModule.shared.trackAPICall(
                endpoint: request.url?.absoluteString ?? "unknown",
                method: request.httpMethod ?? "GET",
                headers: request.allHTTPHeaderFields,
                body: request.httpBody,
                response: response,
                responseData: data,
                error: error
            )
            
            completionHandler(data, response, error)
        }
    }
}