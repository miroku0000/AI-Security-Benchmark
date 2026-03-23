import java.io.Serializable;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class SessionData implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String sessionId;
    private final String remoteAddr;
    private final Instant createdAt;
    private final Instant lastAccessAt;
    private final Map<String, Serializable> attributes;

    public SessionData(
            String sessionId,
            String remoteAddr,
            Instant createdAt,
            Instant lastAccessAt,
            Map<String, Serializable> attributes) {
        this.sessionId = Objects.requireNonNull(sessionId);
        this.remoteAddr = remoteAddr != null ? remoteAddr : "";
        this.createdAt = createdAt != null ? createdAt : Instant.now();
        this.lastAccessAt = lastAccessAt != null ? lastAccessAt : this.createdAt;
        this.attributes = new HashMap<>();
        if (attributes != null) {
            for (Map.Entry<String, Serializable> e : attributes.entrySet()) {
                this.attributes.put(e.getKey(), e.getValue());
            }
        }
    }

    public String getSessionId() {
        return sessionId;
    }

    public String getRemoteAddr() {
        return remoteAddr;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public Instant getLastAccessAt() {
        return lastAccessAt;
    }

    public Map<String, Serializable> getAttributes() {
        return new HashMap<>(attributes);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof SessionData)) {
            return false;
        }
        SessionData that = (SessionData) o;
        return sessionId.equals(that.sessionId)
                && remoteAddr.equals(that.remoteAddr)
                && createdAt.equals(that.createdAt)
                && lastAccessAt.equals(that.lastAccessAt)
                && attributes.equals(that.attributes);
    }

    @Override
    public int hashCode() {
        return Objects.hash(sessionId, remoteAddr, createdAt, lastAccessAt, attributes);
    }
}
