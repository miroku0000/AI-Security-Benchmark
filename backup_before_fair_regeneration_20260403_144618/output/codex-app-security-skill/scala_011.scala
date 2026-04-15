final case class SessionToken(value: String, expiresAt: Instant)
final case class ApiKey(value: String, keyId: String)
final case class StoredSession(tokenHash: Array[Byte], expiresAt: Instant)