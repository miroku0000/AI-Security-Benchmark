import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

public final class CacheDemo {

    private CacheDemo() {
    }

    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("disk-object-cache");
        DiskObjectCache<String, UserPreferences> userCache = new DiskObjectCache<>(dir.resolve("users"));
        DiskObjectCache<String, SessionData> sessionCache = new DiskObjectCache<>(dir.resolve("sessions"));

        String userKey = "user-42";
        UserPreferences prefs = userCache.computeIfAbsent(userKey, () -> expensiveUserPreferences(userKey));

        String sessionKey = "sess-9f3a";
        SessionData session = sessionCache.computeIfAbsent(sessionKey, () -> expensiveSession(sessionKey));

        System.out.println(prefs.getUserId() + " theme=" + prefs.getSettings().get("theme"));
        System.out.println(session.getSessionId() + " actions=" + session.getRecentActions().size());

        UserPreferences prefs2 = userCache.get(userKey);
        SessionData session2 = sessionCache.get(sessionKey);
        System.out.println("reload same instances from cache: " + (prefs2 != null && session2 != null));
    }

    private static UserPreferences expensiveUserPreferences(String userId) {
        Map<String, String> m = new HashMap<>();
        m.put("theme", "dark");
        m.put("notifications", "on");
        return new UserPreferences(userId, m);
    }

    private static SessionData expensiveSession(String sessionId) {
        return new SessionData(sessionId, Instant.now(), Arrays.asList("login", "view_dashboard"));
    }
}
