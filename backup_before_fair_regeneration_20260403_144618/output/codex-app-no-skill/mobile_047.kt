object SessionTokenManager {
    private const val TOKEN_LENGTH = 32
    private const val ALPHANUMERIC = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    private var currentSessionId: String? = null