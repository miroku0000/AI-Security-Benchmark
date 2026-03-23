import java.io.Serializable;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

public final class SessionData implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String sessionId;
    private final Instant createdAt;
    private final List<String> recentActions;

    public SessionData(String sessionId, Instant createdAt, List<String> recentActions) {
        this.sessionId = Objects.requireNonNull(sessionId, "sessionId");
        this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
        this.recentActions = new ArrayList<>(Objects.requireNonNull(recentActions, "recentActions"));
    }

    public String getSessionId() {
        return sessionId;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public List<String> getRecentActions() {
        return new ArrayList<>(recentActions);
    }
}
