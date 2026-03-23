import java.io.BufferedInputStream;
import java.io.BufferedOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.HashMap;
import java.util.HexFormat;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Supplier;

public final class DiskCacheSystem {

    private DiskCacheSystem() {}

    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("disk-object-cache");
        DiskObjectCache cache = new DiskObjectCache(dir);
        AtomicInteger expensiveCalls = new AtomicInteger(0);

        UserPreferences prefs = cache.getOrCompute("user:42:prefs", () -> {
            expensiveCalls.incrementAndGet();
            Map<String, String> s = new HashMap<>();
            s.put("lang", "en");
            s.put("tz", "UTC");
            return new UserPreferences("42", s, "dark", true);
        });

        UserPreferences prefsCached = cache.getOrCompute("user:42:prefs", () -> {
            expensiveCalls.incrementAndGet();
            Map<String, String> s = new HashMap<>();
            s.put("lang", "en");
            return new UserPreferences("42", s, "light", false);
        });

        Map<String, Serializable> attrs = new HashMap<>();
        attrs.put("prefs", prefsCached);
        attrs.put("cartId", "cart-9001");

        SessionData session = cache.getOrCompute("sess:abc123", () -> {
            expensiveCalls.incrementAndGet();
            return new SessionData("abc123", "127.0.0.1", Instant.now(), Instant.now(), attrs);
        });

        SessionData sessionFromDisk = cache.get("sess:abc123");

        System.out.println("expensiveCalls=" + expensiveCalls.get());
        System.out.println("prefsEqual=" + prefsCached.equals(prefs));
        System.out.println("sessionOk=" + (sessionFromDisk != null && sessionFromDisk.getSessionId().equals(session.getSessionId())));
        System.out.println("cacheDir=" + dir);
    }
}

final class DiskObjectCache {

    private final Path cacheDirectory;
    private final ConcurrentHashMap<String, Object> memory = new ConcurrentHashMap<>();

    DiskObjectCache(Path cacheDirectory) throws IOException {
        this.cacheDirectory = Objects.requireNonNull(cacheDirectory);
        Files.createDirectories(this.cacheDirectory);
    }

    Path getCacheDirectory() {
        return cacheDirectory;
    }

    <T extends Serializable> T getOrCompute(String key, Supplier<T> expensiveComputation) throws IOException {
        Objects.requireNonNull(key);
        Objects.requireNonNull(expensiveComputation);
        @SuppressWarnings("unchecked")
        T mem = (T) memory.get(key);
        if (mem != null) {
            return mem;
        }
        Path file = fileForKey(key);
        if (Files.isRegularFile(file)) {
            try {
                T loaded = readObject(file);
                if (loaded != null) {
                    memory.put(key, loaded);
                    return loaded;
                }
            } catch (ClassNotFoundException e) {
                Files.deleteIfExists(file);
            }
        }
        T computed = expensiveComputation.get();
        if (computed == null) {
            throw new IllegalStateException("Computation returned null for key: " + key);
        }
        writeObjectAtomic(file, computed);
        memory.put(key, computed);
        return computed;
    }

    void put(String key, Serializable value) throws IOException {
        Objects.requireNonNull(key);
        Objects.requireNonNull(value);
        Path file = fileForKey(key);
        writeObjectAtomic(file, value);
        memory.put(key, value);
    }

    @SuppressWarnings("unchecked")
    <T extends Serializable> T get(String key) throws IOException, ClassNotFoundException {
        Objects.requireNonNull(key);
        Object mem = memory.get(key);
        if (mem != null) {
            return (T) mem;
        }
        Path file = fileForKey(key);
        if (!Files.isRegularFile(file)) {
            return null;
        }
        T loaded = readObject(file);
        if (loaded != null) {
            memory.put(key, loaded);
        }
        return loaded;
    }

    boolean invalidate(String key) throws IOException {
        Objects.requireNonNull(key);
        memory.remove(key);
        Path file = fileForKey(key);
        return Files.deleteIfExists(file);
    }

    private Path fileForKey(String key) {
        String safe = sha256Hex(key);
        return cacheDirectory.resolve(safe + ".cache");
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static <T extends Serializable> T readObject(Path file) throws IOException, ClassNotFoundException {
        try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(Files.newInputStream(file)))) {
            @SuppressWarnings("unchecked")
            T obj = (T) ois.readObject();
            return obj;
        }
    }

    private static void writeObjectAtomic(Path target, Serializable value) throws IOException {
        Path dir = target.getParent();
        if (dir != null) {
            Files.createDirectories(dir);
        }
        Path parent = dir != null ? dir : target.toAbsolutePath().getParent();
        Path tmp = Files.createTempFile(parent, ".cache-", ".tmp");
        try {
            try (ObjectOutputStream oos = new ObjectOutputStream(new BufferedOutputStream(Files.newOutputStream(tmp)))) {
                oos.writeObject(value);
                oos.flush();
            }
            Files.move(tmp, target, java.nio.file.StandardCopyOption.REPLACE_EXISTING, java.nio.file.StandardCopyOption.ATOMIC_MOVE);
        } finally {
            Files.deleteIfExists(tmp);
        }
    }
}

final class UserPreferences implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String userId;
    private final Map<String, String> settings;
    private final String theme;
    private final boolean notificationsEnabled;

    UserPreferences(String userId, Map<String, String> settings, String theme, boolean notificationsEnabled) {
        this.userId = Objects.requireNonNull(userId);
        this.settings = new HashMap<>(settings);
        this.theme = theme != null ? theme : "default";
        this.notificationsEnabled = notificationsEnabled;
    }

    String getUserId() {
        return userId;
    }

    Map<String, String> getSettings() {
        return new HashMap<>(settings);
    }

    String getTheme() {
        return theme;
    }

    boolean isNotificationsEnabled() {
        return notificationsEnabled;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (!(o instanceof UserPreferences)) {
            return false;
        }
        UserPreferences that = (UserPreferences) o;
        return notificationsEnabled == that.notificationsEnabled
                && userId.equals(that.userId)
                && settings.equals(that.settings)
                && theme.equals(that.theme);
    }

    @Override
    public int hashCode() {
        return Objects.hash(userId, settings, theme, notificationsEnabled);
    }

    @Override
    public String toString() {
        return "UserPreferences{userId='" + userId + "', theme='" + theme + "', notifications=" + notificationsEnabled + "}";
    }
}

final class SessionData implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String sessionId;
    private final String remoteAddr;
    private final Instant createdAt;
    private final Instant lastAccessAt;
    private final Map<String, Serializable> attributes;

    SessionData(
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

    String getSessionId() {
        return sessionId;
    }

    String getRemoteAddr() {
        return remoteAddr;
    }

    Instant getCreatedAt() {
        return createdAt;
    }

    Instant getLastAccessAt() {
        return lastAccessAt;
    }

    Map<String, Serializable> getAttributes() {
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
