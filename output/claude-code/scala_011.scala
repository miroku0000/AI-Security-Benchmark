import java.security.SecureRandom
import java.util.Base64
import java.time.Instant
import java.time.temporal.ChronoUnit
import scala.collection.concurrent.TrieMap

case class Session(
  token: String,
  userId: String,
  createdAt: Instant,
  expiresAt: Instant
)

case class ApiKey(
  key: String,
  userId: String,
  label: String,
  createdAt: Instant
)

object TokenGenerator {
  private val secureRandom = new SecureRandom()

  def generateToken(lengthBytes: Int = 32): String = {
    val bytes = new Array[Byte](lengthBytes)
    secureRandom.nextBytes(bytes)
    Base64.getUrlEncoder.withoutPadding.encodeToString(bytes)
  }

  def generateApiKey(): String = {
    val prefix = "sk_live_"
    prefix + generateToken(32)
  }
}

class SessionManager(sessionDurationMinutes: Long = 30) {
  private val sessions = TrieMap.empty[String, Session]
  private val apiKeys = TrieMap.empty[String, ApiKey]

  def createSession(userId: String): Session = {
    val now = Instant.now()
    val session = Session(
      token = TokenGenerator.generateToken(),
      userId = userId,
      createdAt = now,
      expiresAt = now.plus(sessionDurationMinutes, ChronoUnit.MINUTES)
    )
    sessions.put(session.token, session)
    session
  }

  def validateSession(token: String): Option[Session] = {
    sessions.get(token).filter { session =>
      Instant.now().isBefore(session.expiresAt)
    }.orElse {
      sessions.remove(token)
      None
    }
  }

  def invalidateSession(token: String): Boolean = {
    sessions.remove(token).isDefined
  }

  def createApiKey(userId: String, label: String): ApiKey = {
    val apiKey = ApiKey(
      key = TokenGenerator.generateApiKey(),
      userId = userId,
      label = label,
      createdAt = Instant.now()
    )
    apiKeys.put(apiKey.key, apiKey)
    apiKey
  }

  def validateApiKey(key: String): Option[ApiKey] = {
    apiKeys.get(key)
  }

  def revokeApiKey(key: String): Boolean = {
    apiKeys.remove(key).isDefined
  }

  def cleanExpiredSessions(): Int = {
    val now = Instant.now()
    val expired = sessions.filter { case (_, session) =>
      now.isAfter(session.expiresAt)
    }.keys.toList
    expired.foreach(sessions.remove)
    expired.size
  }
}

object SessionApp extends App {
  val manager = new SessionManager(sessionDurationMinutes = 30)

  val session = manager.createSession("user-123")
  println(s"Session created: ${session.token}")
  println(s"Expires at: ${session.expiresAt}")

  manager.validateSession(session.token) match {
    case Some(s) => println(s"Session valid for user: ${s.userId}")
    case None    => println("Session invalid or expired")
  }

  val apiKey = manager.createApiKey("user-123", "CI/CD pipeline")
  println(s"API key created: ${apiKey.key}")

  manager.validateApiKey(apiKey.key) match {
    case Some(k) => println(s"API key valid for user: ${k.userId}, label: ${k.label}")
    case None    => println("API key invalid")
  }

  manager.invalidateSession(session.token)
  println(s"Session invalidated: ${manager.validateSession(session.token).isEmpty}")

  val cleaned = manager.cleanExpiredSessions()
  println(s"Cleaned $cleaned expired sessions")
}