private static func sanitizeValue(key: String, value: Any) -> Any {
        if let string = value as? String {
            if isSensitiveKey(key) {
                if key.lowercased().contains("email") {
                    return redactedEmail(string)
                }
                if key.lowercased().contains("user") || key.lowercased().contains("id") {
                    return redactedUserID(string)
                }
                return redactedToken(string)
            }
            if looksLikeEmail(string) {
                return redactedEmail(string)
            }
            if looksLikeToken(key: key, value: string) {
                return redactedToken(string)
            }
            return string
        }