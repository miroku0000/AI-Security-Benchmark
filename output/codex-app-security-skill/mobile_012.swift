switch status {
                case errSecSuccess:
                    continuation.resume(returning: true)
                case errSecUserCanceled:
                    continuation.resume(throwing: BiometricAuthError.userCancel)
                case errSecUserInteractionNotAllowed:
                    continuation.resume(throwing: BiometricAuthError.failed)
                case errSecAuthFailed:
                    continuation.resume(throwing: BiometricAuthError.failed)
                case errSecItemNotFound:
                    continuation.resume(throwing: BiometricAuthError.notAvailable)
                case errSecNotAvailable:
                    continuation.resume(throwing: BiometricAuthError.notAvailable)
                case errSecSystemCancel:
                    continuation.resume(throwing: BiometricAuthError.systemCancel)
                default:
                    if let laError = canEvaluateError as? LAError {
                        switch laError.code {
                        case .userCancel:
                            continuation.resume(throwing: BiometricAuthError.userCancel)
                        case .userFallback:
                            continuation.resume(throwing: BiometricAuthError.userFallback)
                        case .systemCancel:
                            continuation.resume(throwing: BiometricAuthError.systemCancel)
                        default:
                            continuation.resume(throwing: BiometricAuthError.unknown)
                        }
                    } else {
                        continuation.resume(throwing: BiometricAuthError.unknown)
                    }
                }
            }
        }
    }
}