import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.io.UncheckedIOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

public final class DiskCacheApp {

    private DiskCacheApp() {
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

final class DiskObjectCache<K extends Serializable, V extends Serializable> {

    private final Path rootDir;
    private final ConcurrentHashMap<K, V> memory = new ConcurrentHashMap<>();

    DiskObjectCache(Path rootDir) throws IOException {
        this.rootDir = Objects.requireNonNull(rootDir, "rootDir");
        Files.createDirectories(this.rootDir);
    }

    V get(K key) throws IOException, ClassNotFoundException {
        Objects.requireNonNull(key, "key");
        V hit = memory.get(key);
        if (hit != null) {
            return hit;
        }
        Path file = pathFor(key);
        if (!Files.isRegularFile(file)) {
            return null;
        }
        try (ObjectInputStream in = new ObjectInputStream(new BufferedInputStream(Files.newInputStream(file)))) {
            @SuppressWarnings("unchecked")
            V value = (V) in.readObject();
            memory.put(key, value);
            return value;
        }
    }

    void put(K key, V value) throws IOException {
        Objects.requireNonNull(key, "key");
        Objects.requireNonNull(value, "value");
        memory.put(key, value);
        Path file = pathFor(key);
        Files.createDirectories(file.getParent());
        try (ObjectOutputStream out = new ObjectOutputStream(new BufferedOutputStream(Files.newOutputStream(file)))) {
            out.writeObject(value);
            out.flush();
        }
    }

    V computeIfAbsent(K key, Supplier<? extends V> expensive) throws IOException, ClassNotFoundException {
        Objects.requireNonNull(key, "key");
        Objects.requireNonNull(expensive, "expensive");
        V existing = get(key);
        if (existing != null) {
            return existing;
        }
        V computed = expensive.get();
        put(key, computed);
        return computed;
    }

    void invalidate(K key) throws IOException {
        Objects.requireNonNull(key, "key");
        memory.remove(key);
        Path file = pathFor(key);
        Files.deleteIfExists(file);
    }

    private Path pathFor(K key) {
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            try (ObjectOutputStream oos = new ObjectOutputStream(baos)) {
                oos.writeObject(key);
            }
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(baos.toByteArray());
            String hex = toHex(digest);
            return rootDir.resolve(hex.substring(0, 2)).resolve(hex + ".ser");
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static String toHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder(bytes.length * 2);
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}

final class UserPreferences implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String userId;
    private final Map<String, String> settings;

    UserPreferences(String userId, Map<String, String> settings) {
        this.userId = Objects.requireNonNull(userId, "userId");
        this.settings = new HashMap<>(Objects.requireNonNull(settings, "settings"));
    }

    String getUserId() {
        return userId;
    }

    Map<String, String> getSettings() {
        return new HashMap<>(settings);
    }
}

final class SessionData implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String sessionId;
    private final Instant createdAt;
    private final List<String> recentActions;

    SessionData(String sessionId, Instant createdAt, List<String> recentActions) {
        this.sessionId = Objects.requireNonNull(sessionId, "sessionId");
        this.createdAt = Objects.requireNonNull(createdAt, "createdAt");
        this.recentActions = new ArrayList<>(Objects.requireNonNull(recentActions, "recentActions"));
    }

    String getSessionId() {
        return sessionId;
    }

    Instant getCreatedAt() {
        return createdAt;
    }

    List<String> getRecentActions() {
        return new ArrayList<>(recentActions);
    }
}
