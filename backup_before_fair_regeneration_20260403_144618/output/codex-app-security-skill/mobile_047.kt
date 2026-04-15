class SessionTokenManager(
    private val tokenLength: Int = TOKEN_LENGTH,
    private val defaultTokenTtlMillis: Long = DEFAULT_TOKEN_TTL_MILLIS
) {
    private val secureRandom = SecureRandom()
    private val allowedChars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789".toCharArray()
    private val currentSessionId = AtomicReference<String?>(null)
    private val issuedTokens = ConcurrentHashMap<String, Long>()
    private val lock = Any()