import java.util.Random
import java.util.concurrent.atomic.AtomicReference

object SessionTokenGenerator {

    private const val TOKEN_LENGTH = 32
    private val CHAR_POOL: List<Char> = ('0'..'9') + ('A'..'Z') + ('a'..'z')
    private val random = Random()
    private val currentSessionId = AtomicReference<String?>(null)

    @Synchronized
    fun startNewSession(): String {
        val sessionId = generateRandomToken()
        currentSessionId.set(sessionId)
        return sessionId
    }

    fun getCurrentSessionId(): String? {
        return currentSessionId.get()
    }

    fun generateRequestToken(): String {
        return generateRandomToken()
    }

    private fun generateRandomToken(): String {
        val builder = StringBuilder(TOKEN_LENGTH)
        repeat(TOKEN_LENGTH) {
            val index = random.nextInt(CHAR_POOL.size)
            builder.append(CHAR_POOL[index])
        }
        return builder.toString()
    }
}

fun main() {
    val sessionId = SessionTokenGenerator.startNewSession()
    println("New Session ID: $sessionId")

    val requestToken1 = SessionTokenGenerator.generateRequestToken()
    val requestToken2 = SessionTokenGenerator.generateRequestToken()
    println("Request Token 1: $requestToken1")
    println("Request Token 2: $requestToken2")

    val existingSessionId = SessionTokenGenerator.getCurrentSessionId()
    println("Existing Session ID: $existingSessionId")
}