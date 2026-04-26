import Foundation

public enum AnalyticsLogLevel: String {
    case debug = "DEBUG"
    case info = "INFO"
    case warning = "WARNING"
    case error = "ERROR"
}

public enum AuthFlowStep: String {
    case loginStarted
    case loginSucceeded
    case loginFailed
    case logoutStarted
    case logoutSucceeded
    case logoutFailed
    case tokenRefreshStarted
    case tokenRefreshSucceeded
    case tokenRefreshFailed
    case signupStarted
    case signupSucceeded
    case signupFailed
}

public enum UserDataChangeType: String {
    case profileUpdated
    case passwordChanged
    case preferencesUpdated
    case accountDeleted
    case emailUpdated
    case phoneUpdated
    case custom
}

public struct APICallRecord {
    public let endpoint: String
    public let method: String
    public let requestHeaders: [String: String]
    public let requestBody: Any?
    public let statusCode: Int?
    public let responseHeaders: [String: String]
    public let responseBody: Any?
    public let durationMs: Int?
    public let requestID: String?

    public init(
        endpoint: String,
        method: String,
        requestHeaders: [String: String] = [:],
        requestBody: Any? = nil,
        statusCode: Int? = nil,
        responseHeaders: [String: String] = [:],
        responseBody: Any? = nil,
        durationMs: Int? = nil,
        requestID: String? = nil
    ) {
        self.endpoint = endpoint
        self.method = method
        self.requestHeaders = requestHeaders
        self.requestBody = requestBody
        self.statusCode = statusCode
        self.responseHeaders = responseHeaders
        self.responseBody = responseBody
        self.durationMs = durationMs
        self.requestID = requestID
    }
}

public struct AppErrorRecord {
    public let domain: String
    public let code: Int
    public let message: String
    public let function: String
    public let file: String
    public let line: Int
    public let metadata: [String: Any]

    public init(
        domain: String,
        code: Int,
        message: String,
        function: String = #function,
        file: String = #fileID,
        line: Int = #line,
        metadata: [String: Any] = [:]
    ) {
        self.domain = domain
        self.code = code
        self.message = message
        self.function = function
        self.file = file
        self.line = line
        self.metadata = metadata
    }
}

public final class AnalyticsDebugger {
    public static let shared = AnalyticsDebugger()

    public var isEnabled: Bool
    public var consoleMirrorEnabled: Bool

    private let queue = DispatchQueue(label: "com.example.analyticsdebugger", qos: .utility)
    private let isoFormatter: ISO8601DateFormatter

    public init(isEnabled: Bool = true, consoleMirrorEnabled: Bool = true) {
        self.isEnabled = isEnabled
        self.consoleMirrorEnabled = consoleMirrorEnabled
        self.isoFormatter = ISO8601DateFormatter()
        self.isoFormatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    }

    public func logUserInteraction(
        name: String,
        screen: String,
        metadata: [String: Any] = [:]
    ) {
        log(
            category: "user_interaction",
            level: .info,
            message: "User interaction recorded",
            attributes: [
                "event_name": name,
                "screen": screen,
                "metadata": sanitize(metadata)
            ]
        )
    }

    public func logAppBehavior(
        name: String,
        metadata: [String: Any] = [:]
    ) {
        log(
            category: "app_behavior",
            level: .debug,
            message: "App behavior event recorded",
            attributes: [
                "event_name": name,
                "metadata": sanitize(metadata)
            ]
        )
    }

    public func logAuthFlow(
        step: AuthFlowStep,
        userID: String? = nil,
        email: String? = nil,
        metadata: [String: Any] = [:]
    ) {
        log(
            category: "auth_flow",
            level: step.rawValue.lowercased().contains("failed") ? .warning : .info,
            message: "Authentication flow event",
            attributes: [
                "step": step.rawValue,
                "user_id": redactIdentifier(userID),
                "email": redactEmail(email),
                "metadata": sanitize(metadata)
            ]
        )
    }

    public func logAPICall(_ record: APICallRecord) {
        let attributes: [String: Any] = [
            "endpoint": sanitizeURLPath(record.endpoint),
            "method": record.method.uppercased(),
            "request_headers": sanitize(record.requestHeaders),
            "request_body": sanitize(record.requestBody),
            "status_code": record.statusCode as Any,
            "response_headers": sanitize(record.responseHeaders),
            "response_body": sanitize(record.responseBody),
            "duration_ms": record.durationMs as Any,
            "request_id": redactIdentifier(record.requestID)
        ]

        let level: AnalyticsLogLevel = {
            guard let statusCode = record.statusCode else { return .debug }
            switch statusCode {
            case 200..<400: return .info
            case 400..<500: return .warning
            default: return .error
            }
        }()

        log(
            category: "api_call",
            level: level,
            message: "API call recorded",
            attributes: attributes
        )
    }

    public func logUserDataChange(
        type: UserDataChangeType,
        userID: String? = nil,
        fieldsChanged: [String],
        metadata: [String: Any] = [:]
    ) {
        log(
            category: "user_data_change",
            level: .info,
            message: "User data changed",
            attributes: [
                "type": type.rawValue,
                "user_id": redactIdentifier(userID),
                "fields_changed": fieldsChanged,
                "metadata": sanitize(metadata)
            ]
        )
    }

    public func logError(_ errorRecord: AppErrorRecord) {
        log(
            category: "error",
            level: .error,
            message: errorRecord.message,
            attributes: [
                "domain": errorRecord.domain,
                "code": errorRecord.code,
                "function": errorRecord.function,
                "file": errorRecord.file,
                "line": errorRecord.line,
                "metadata": sanitize(errorRecord.metadata)
            ]
        )
    }

    public func logNSError(
        _ error: NSError,
        metadata: [String: Any] = [:],
        function: String = #function,
        file: String = #fileID,
        line: Int = #line
    ) {
        logError(
            AppErrorRecord(
                domain: error.domain,
                code: error.code,
                message: error.localizedDescription,
                function: function,
                file: file,
                line: line,
                metadata: metadata
            )
        )
    }

    private func log(
        category: String,
        level: AnalyticsLogLevel,
        message: String,
        attributes: [String: Any]
    ) {
        guard isEnabled else { return }

        queue.async {
            let payload: [String: Any] = [
                "timestamp": self.isoFormatter.string(from: Date()),
                "category": category,
                "level": level.rawValue,
                "message": message,
                "attributes": attributes
            ]

            let text = self.stringify(payload)
            NSLog("%@", text)

            if self.consoleMirrorEnabled {
                print(text)
            }
        }
    }

    private func stringify(_ payload: [String: Any]) -> String {
        if JSONSerialization.isValidJSONObject(payload),
           let data = try? JSONSerialization.data(withJSONObject: payload, options: [.sortedKeys]),
           let string = String(data: data, encoding: .utf8) {
            return string
        }

        return "\(payload)"
    }

    private func sanitize(_ value: Any?) -> Any {
        guard let value else { return NSNull() }

        if let dict = value as? [String: Any] {
            var output: [String: Any] = [:]
            for (key, value) in dict {
                output[key] = sanitize(key: key, value: value)
            }
            return output
        }

        if let dict = value as? [String: String] {
            var output: [String: Any] = [:]
            for (key, value) in dict {
                output[key] = sanitize(key: key, value: value)
            }
            return output
        }

        if let array = value as? [Any] {
            return array.map { sanitize($0) }
        }

        if let string = value as? String {
            return redactStringIfSensitive(string)
        }

        if let url = value as? URL {
            return sanitizeURLPath(url.absoluteString)
        }

        return value
    }

    private func sanitize(key: String, value: Any) -> Any {
        let lower = key.lowercased()

        if lower.contains("token") ||
            lower.contains("authorization") ||
            lower.contains("password") ||
            lower.contains("secret") ||
            lower.contains("cookie") ||
            lower.contains("session") ||
            lower.contains("api_key") ||
            lower.contains("apikey") {
            return redactedPlaceholder(for: key)
        }

        if lower.contains("email") {
            if let string = value as? String {
                return redactEmail(string)
            }
            return "[REDACTED_EMAIL]"
        }

        if lower == "user_id" || lower == "userid" || lower == "user" || lower.hasSuffix("_id") {
            if let string = value as? String {
                return redactIdentifier(string)
            }
            return "[REDACTED_ID]"
        }

        if lower.contains("url") || lower.contains("endpoint") || lower.contains("path") {
            if let string = value as? String {
                return sanitizeURLPath(string)
            }
            if let url = value as? URL {
                return sanitizeURLPath(url.absoluteString)
            }
        }

        return sanitize(value)
    }

    private func redactStringIfSensitive(_ string: String) -> String {
        if string.contains("@"), string.contains(".") {
            return redactEmail(string)
        }

        if looksLikeToken(string) {
            return "[REDACTED_TOKEN]"
        }

        return string
    }

    private func redactIdentifier(_ value: String?) -> String {
        guard let value, !value.isEmpty else { return "[NONE]" }
        let suffix = String(value.suffix(min(4, value.count)))
        return "[REDACTED_ID:\(suffix)]"
    }

    private func redactEmail(_ value: String?) -> String {
        guard let value, !value.isEmpty else { return "[NONE]" }
        let parts = value.split(separator: "@", maxSplits: 1).map(String.init)
        guard parts.count == 2 else { return "[REDACTED_EMAIL]" }

        let local = parts[0]
        let domain = parts[1]
        let localPrefix = String(local.prefix(1))
        let domainParts = domain.split(separator: ".", maxSplits: 1).map(String.init)

        if domainParts.count == 2 {
            let domainPrefix = String(domainParts[0].prefix(1))
            return "\(localPrefix)***@\(domainPrefix)***.\(domainParts[1])"
        }

        return "\(localPrefix)***@***"
    }

    private func sanitizeURLPath(_ path: String) -> String {
        guard var components = URLComponents(string: path) else {
            return path.replacingOccurrences(of: #"([?&])(token|access_token|refresh_token|email|user_id|userid)=[^&]+"#, with: "$1$2=[REDACTED]", options: .regularExpression)
        }

        if let queryItems = components.queryItems, !queryItems.isEmpty {
            components.queryItems = queryItems.map { item in
                let lower = item.name.lowercased()
                if lower.contains("token") || lower.contains("email") || lower.contains("user") || lower.contains("auth") {
                    return URLQueryItem(name: item.name, value: "[REDACTED]")
                }
                return item
            }
        }

        return components.string ?? path
    }

    private func redactedPlaceholder(for key: String) -> String {
        let normalized = key.uppercased().replacingOccurrences(of: " ", with: "_")
        return "[REDACTED_\(normalized)]"
    }

    private func looksLikeToken(_ value: String) -> Bool {
        if value.count >= 24 { return true }
        if value.hasPrefix("Bearer ") { return true }
        if value.split(separator: ".").count == 3 { return true }
        return false
    }
}

public enum ExampleError: Error {
    case unauthorized
    case network
}

@main
struct DemoRunner {
    static func main() {
        let analytics = AnalyticsDebugger.shared

        analytics.logUserInteraction(
            name: "login_button_tapped",
            screen: "LoginViewController",
            metadata: [
                "button_title": "Sign In",
                "campaign": "spring_launch"
            ]
        )

        analytics.logAuthFlow(
            step: .loginStarted,
            userID: "usr_1234567890",
            email: "person@example.com",
            metadata: [
                "provider": "email_password",
                "device": "iPhone"
            ]
        )

        analytics.logAPICall(
            APICallRecord(
                endpoint: "https://api.example.com/v1/session?email=person@example.com&token=abc123secret",
                method: "POST",
                requestHeaders: [
                    "Authorization": "Bearer abc.def.ghi",
                    "Content-Type": "application/json"
                ],
                requestBody: [
                    "email": "person@example.com",
                    "password": "super-secret-password",
                    "device_id": "device-1234"
                ],
                statusCode: 401,
                responseHeaders: [
                    "X-Request-ID": "req_abcdef123456"
                ],
                responseBody: [
                    "error": "Unauthorized",
                    "token": "new-secret-token"
                ],
                durationMs: 482,
                requestID: "req_abcdef123456"
            )
        )

        analytics.logUserDataChange(
            type: .profileUpdated,
            userID: "usr_1234567890",
            fieldsChanged: ["display_name", "email"],
            metadata: [
                "email": "person@example.com",
                "source": "settings_screen"
            ]
        )

        analytics.logAppBehavior(
            name: "background_refresh_completed",
            metadata: [
                "items_synced": 12,
                "last_endpoint": "https://api.example.com/v1/profile?user_id=usr_1234567890"
            ]
        )

        let nsError = NSError(domain: "com.example.auth", code: 1001, userInfo: [
            NSLocalizedDescriptionKey: "Token expired"
        ])
        analytics.logNSError(
            nsError,
            metadata: [
                "token": "expired-token-value",
                "user_id": "usr_1234567890"
            ]
        )

        Thread.sleep(forTimeInterval: 0.5)
    }
}