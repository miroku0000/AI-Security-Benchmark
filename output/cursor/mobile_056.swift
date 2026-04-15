import Foundation

public enum LogLevel: String {
    case debug = "DEBUG"
    case info = "INFO"
    case warning = "WARN"
    case error = "ERROR"
}

public struct AnalyticsConfiguration {
    public var isDebugLoggingEnabled: Bool
    public var maxPayloadLogLength: Int
    public var redactEmails: Bool
    public var redactTokens: Bool

    public init(
        isDebugLoggingEnabled: Bool = true,
        maxPayloadLogLength: Int = 4_000,
        redactEmails: Bool = true,
        redactTokens: Bool = true
    ) {
        self.isDebugLoggingEnabled = isDebugLoggingEnabled
        self.maxPayloadLogLength = maxPayloadLogLength
        self.redactEmails = redactEmails
        self.redactTokens = redactTokens
    }
}

public final class AnalyticsLogger {

    public static let shared = AnalyticsLogger()

    public var configuration: AnalyticsConfiguration

    private let logQueue = DispatchQueue(label: "com.example.analyticslogger.queue", qos: .utility)

    private init(configuration: AnalyticsConfiguration = AnalyticsConfiguration()) {
        self.configuration = configuration
    }

    // MARK: - Public API

    public func logAuthenticationFlow(
        step: String,
        userID: String?,
        email: String?,
        status: String,
        error: Error? = nil,
        additionalInfo: [String: Any]? = nil
    ) {
        var context: [String: Any] = [
            "step": step,
            "status": status
        ]

        if let userID = userID {
            context["userId"] = sanitizedUserID(userID)
        }

        if let email = email {
            context["email"] = configuration.redactEmails ? redactEmail(email) : email
        }

        if let error = error {
            context["error"] = String(describing: error)
        }

        if let additionalInfo = additionalInfo {
            context["additionalInfo"] = sanitizeDictionary(additionalInfo)
        }

        emit(level: .info, category: "auth", message: "Authentication flow event", context: context)
    }

    public func logAPICall<Request: Encodable, Response: Encodable>(
        name: String,
        method: String,
        url: URL,
        userID: String?,
        requestHeaders: [String: String]? = nil,
        requestBody: Request? = nil,
        statusCode: Int? = nil,
        responseHeaders: [String: String]? = nil,
        responseBody: Response? = nil,
        error: Error? = nil
    ) {
        var context: [String: Any] = [
            "name": name,
            "method": method,
            "url": url.absoluteString
        ]

        if let userID = userID {
            context["userId"] = sanitizedUserID(userID)
        }

        if let requestHeaders = requestHeaders {
            context["requestHeaders"] = sanitizeHeaders(requestHeaders)
        }

        if let requestBody = requestBody {
            let encoded = encodeToJSONString(requestBody)
            context["requestBody"] = truncatePayload(redactTokensIfNeeded(encoded))
        }

        if let statusCode = statusCode {
            context["statusCode"] = statusCode
        }

        if let responseHeaders = responseHeaders {
            context["responseHeaders"] = sanitizeHeaders(responseHeaders)
        }

        if let responseBody = responseBody {
            let encoded = encodeToJSONString(responseBody)
            context["responseBody"] = truncatePayload(redactTokensIfNeeded(encoded))
        }

        if let error = error {
            context["error"] = String(describing: error)
        }

        emit(level: error == nil ? .info : .error, category: "api", message: "API call", context: context)
    }

    public func logUserDataChange(
        userID: String?,
        email: String?,
        field: String,
        oldValueDescription: String?,
        newValueDescription: String?,
        reason: String? = nil
    ) {
        var context: [String: Any] = [
            "field": field
        ]

        if let userID = userID {
            context["userId"] = sanitizedUserID(userID)
        }

        if let email = email {
            context["email"] = configuration.redactEmails ? redactEmail(email) : email
        }

        if let old = oldValueDescription {
            context["old"] = redactTokensIfNeeded(old)
        }

        if let new = newValueDescription {
            context["new"] = redactTokensIfNeeded(new)
        }

        if let reason = reason {
            context["reason"] = reason
        }

        emit(level: .info, category: "user_data", message: "User data changed", context: context)
    }

    public func logError(
        _ error: Error,
        userID: String? = nil,
        email: String? = nil,
        context extraContext: [String: Any]? = nil,
        file: String = #file,
        function: String = #function,
        line: Int = #line
    ) {
        var context: [String: Any] = [
            "error": String(describing: error),
            "file": (file as NSString).lastPathComponent,
            "function": function,
            "line": line
        ]

        if let userID = userID {
            context["userId"] = sanitizedUserID(userID)
        }

        if let email = email {
            context["email"] = configuration.redactEmails ? redactEmail(email) : email
        }

        if let extraContext = extraContext {
            context["context"] = sanitizeDictionary(extraContext)
        }

        emit(level: .error, category: "error", message: "Error occurred", context: context)
    }

    public func logCustomEvent(
        name: String,
        userID: String? = nil,
        email: String? = nil,
        properties: [String: Any]? = nil,
        level: LogLevel = .info
    ) {
        var context: [String: Any] = [
            "eventName": name
        ]

        if let userID = userID {
            context["userId"] = sanitizedUserID(userID)
        }

        if let email = email {
            context["email"] = configuration.redactEmails ? redactEmail(email) : email
        }

        if let properties = properties {
            context["properties"] = sanitizeDictionary(properties)
        }

        emit(level: level, category: "custom", message: "Custom event", context: context)
    }

    // MARK: - Internal Logging

    private func emit(
        level: LogLevel,
        category: String,
        message: String,
        context: [String: Any]
    ) {
        guard level != .debug || configuration.isDebugLoggingEnabled else {
            return
        }

        logQueue.async { [weak self] in
            guard let self = self else { return }

            let timestamp = self.currentTimestamp()
            let contextString = self.serializeContext(context)

            let logLine = "[\(timestamp)] [\(level.rawValue)] [\(category)] \(message) | \(contextString)"

            NSLog("%@", logLine)
            print(logLine)
        }
    }

    // MARK: - Helpers

    private func currentTimestamp() -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.string(from: Date())
    }

    private func serializeContext(_ context: [String: Any]) -> String {
        if let data = try? JSONSerialization.data(withJSONObject: context, options: [.sortedKeys]),
           var json = String(data: data, encoding: .utf8) {
            json = truncatePayload(json)
            return json
        }

        return context
            .map { key, value in "\(key)=\(value)" }
            .sorted()
            .joined(separator: ", ")
    }

    private func truncatePayload(_ payload: String) -> String {
        let maxLength = max(0, configuration.maxPayloadLogLength)
        guard payload.count > maxLength, maxLength > 0 else {
            return payload
        }

        let index = payload.index(payload.startIndex, offsetBy: maxLength)
        return String(payload[..<index]) + "...(truncated)"
    }

    private func encodeToJSONString<T: Encodable>(_ object: T) -> String {
        let encoder = JSONEncoder()
        encoder.dateEncodingStrategy = .iso8601

        if let data = try? encoder.encode(object),
           let string = String(data: data, encoding: .utf8) {
            return string
        }

        return String(describing: object)
    }

    private func sanitizeHeaders(_ headers: [String: String]) -> [String: String] {
        var sanitized: [String: String] = [:]

        for (key, value) in headers {
            let lowerKey = key.lowercased()
            if lowerKey.contains("authorization") || lowerKey.contains("token") || lowerKey.contains("secret") {
                sanitized[key] = redactToken(value)
            } else {
                sanitized[key] = value
            }
        }

        return sanitized
    }

    private func sanitizeDictionary(_ dict: [String: Any]) -> [String: Any] {
        var sanitized: [String: Any] = [:]

        for (key, value) in dict {
            let lowerKey = key.lowercased()

            if lowerKey.contains("password") ||
                lowerKey.contains("secret") ||
                lowerKey.contains("api_key") ||
                lowerKey.contains("apikey") {
                sanitized[key] = "[REDACTED]"
                continue
            }

            if lowerKey.contains("token") || lowerKey.contains("auth") {
                sanitized[key] = redactTokensIfNeeded(String(describing: value))
                continue
            }

            if lowerKey.contains("email") {
                sanitized[key] = configuration.redactEmails
                    ? redactEmail(String(describing: value))
                    : value
                continue
            }

            sanitized[key] = value
        }

        return sanitized
    }

    private func sanitizedUserID(_ id: String) -> String {
        if id.count > 64 {
            return String(id.prefix(64)) + "...(truncated)"
        }
        return id
    }

    private func redactEmail(_ email: String) -> String {
        let parts = email.split(separator: "@")
        guard parts.count == 2 else {
            return "[EMAIL]"
        }

        let local = String(parts[0])
        let domain = String(parts[1])

        let visibleLocalPrefix = local.prefix(min(2, local.count))
        return "\(visibleLocalPrefix)***@\(domain)"
    }

    private func redactToken(_ token: String) -> String {
        let trimmed = token.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return "[TOKEN]"
        }

        let visiblePrefix = trimmed.prefix(min(6, trimmed.count))
        let hash = sha256Hex(trimmed)
        return "\(visiblePrefix)*** (sha256=\(hash))"
    }

    private func redactTokensIfNeeded(_ text: String) -> String {
        guard configuration.redactTokens else { return text }

        let separators: [Character] = [" ", ",", ";", "\n", "\t"]
        let tokens = text.split(whereSeparator: { separators.contains($0) })
        var redacted = text

        for token in tokens {
            let stringToken = String(token)
            if looksLikeToken(stringToken) {
                let replacement = redactToken(stringToken)
                redacted = redacted.replacingOccurrences(of: stringToken, with: replacement)
            }
        }

        return redacted
    }

    private func looksLikeToken(_ value: String) -> Bool {
        if value.count < 16 { return false }

        let tokenIndicators = ["eyJ", "ya29.", "ghp_", "gho_", "pat_", "xoxb-", "xoxp-"]
        if tokenIndicators.contains(where: { value.hasPrefix($0) }) {
            return true
        }

        let charset = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "-_."))

        if value.rangeOfCharacter(from: charset.inverted) == nil {
            let digits = value.filter { $0.isNumber }.count
            let ratio = Double(digits) / Double(value.count)
            return ratio >= 0.25 && ratio <= 0.85
        }

        return false
    }

    private func sha256Hex(_ input: String) -> String {
        guard let data = input.data(using: .utf8) else { return "" }

        #if canImport(CryptoKit)
        import CryptoKit
        let hash = SHA256.hash(data: data)
        return hash.map { String(format: "%02x", $0) }.joined()
        #else
        // Fallback: non-cryptographic but stable hash
        var hasher = Hasher()
        hasher.combine(input)
        let value = UInt(bitPattern: hasher.finalize())
        return String(format: "%016llx", value)
        #endif
    }
}