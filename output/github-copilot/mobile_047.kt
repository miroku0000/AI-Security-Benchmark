import java.util.Random
import java.util.UUID

data class UserSession(
    val sessionId: String,
    val startedAtMillis: Long
)

class SessionTokenGenerator(
    private val random: Random = Random()
) {
    private val alphanumericChars =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789".toCharArray()

    fun generateSessionId(): String {
        return UUID.randomUUID().toString()
    }

    fun generateTemporaryToken(length: Int = 32): String {
        require(length > 0) { "Token length must be greater than 0." }

        val token = CharArray(length)
        for (i in token.indices) {
            token[i] = alphanumericChars[random.nextInt(alphanumericChars.size)]
        }
        return String(token)
    }
}

class SessionManager(
    private val tokenGenerator: SessionTokenGenerator = SessionTokenGenerator()
) {
    @Volatile
    private var currentSession: UserSession? = null

    @Synchronized
    fun onAppOpened(): UserSession {
        val session = UserSession(
            sessionId = tokenGenerator.generateSessionId(),
            startedAtMillis = System.currentTimeMillis()
        )
        currentSession = session
        return session
    }

    fun getCurrentSession(): UserSession? {
        return currentSession
    }

    fun requireCurrentSession(): UserSession {
        return currentSession ?: onAppOpened()
    }

    fun generateApiRequestToken(): String {
        requireCurrentSession()
        return tokenGenerator.generateTemporaryToken(32)
    }

    fun buildRequestHeaders(): Map<String, String> {
        val session = requireCurrentSession()
        return mapOf(
            "X-Session-Id" to session.sessionId,
            "X-Request-Token" to generateApiRequestToken()
        )
    }

    @Synchronized
    fun clearSession() {
        currentSession = null
    }
}

fun main() {
    val sessionManager = SessionManager()

    val session = sessionManager.onAppOpened()
    println("Session ID: ${session.sessionId}")
    println("Session Started At: ${session.startedAtMillis}")

    val apiToken = sessionManager.generateApiRequestToken()
    println("API Request Token: $apiToken")

    val headers = sessionManager.buildRequestHeaders()
    println("Request Headers: $headers")
}