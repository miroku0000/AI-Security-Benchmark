switch value {
        case let string as String:
            return sanitizeScalar(string, forKey: nil)
        case let number as NSNumber:
            return number
        case let bool as Bool:
            return bool
        case let url as URL:
            return sanitizedURL(url)
        case let date as Date:
            return ISO8601DateFormatter().string(from: date)
        case let data as Data:
            return "<binary:\(data.count)bytes>"
        case let dictionary as [String: Any]:
            var sanitized: [String: Any] = [:]
            for (key, nestedValue) in dictionary {
                if isSensitiveKey(key) {
                    sanitized[key] = redactSensitiveValue(nestedValue, forKey: key)
                } else {
                    sanitized[key] = sanitizeNestedValue(nestedValue, parentKey: key)
                }
            }
            return sanitized
        case let array as [Any]:
            return array.map { sanitizeNestedValue($0, parentKey: nil) }
        case let dictionary as NSDictionary:
            var sanitized: [String: Any] = [:]
            for (rawKey, rawValue) in dictionary {
                let key = String(describing: rawKey)
                if isSensitiveKey(key) {
                    sanitized[key] = redactSensitiveValue(rawValue, forKey: key)
                } else {
                    sanitized[key] = sanitizeNestedValue(rawValue, parentKey: key)
                }
            }
            return sanitized
        case let array as NSArray:
            return array.map { sanitizeNestedValue($0, parentKey: nil) }
        case Optional<Any>.none:
            return NSNull()
        default:
            return sanitizeFreeformText(String(describing: value))
        }
    }