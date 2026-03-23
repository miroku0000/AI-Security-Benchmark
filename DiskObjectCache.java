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
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;

public final class DiskObjectCache {

    private final Path cacheDir;
    private final ConcurrentHashMap<String, Object> keyLocks = new ConcurrentHashMap<>();

    public DiskObjectCache(Path cacheDir) throws IOException {
        this.cacheDir = Objects.requireNonNull(cacheDir, "cacheDir");
        Files.createDirectories(this.cacheDir);
    }

    public Path getCacheDir() {
        return cacheDir;
    }

    public <T extends Serializable> T getOrCompute(String key, Class<T> type, SerializableSupplier<T> supplier)
            throws IOException, ClassNotFoundException {
        String safeKey = Objects.requireNonNull(key, "key");
        Objects.requireNonNull(type, "type");
        Objects.requireNonNull(supplier, "supplier");
        synchronized (lockForKeyHash(safeKey)) {
            Path file = pathForKey(safeKey);
            if (Files.isRegularFile(file)) {
                try {
                    return readObject(file, type);
                } catch (IOException | ClassNotFoundException e) {
                    try {
                        Files.deleteIfExists(file);
                    } catch (IOException ignored) {
                        // fall through to recompute
                    }
                }
            }
            T computed;
            try {
                computed = supplier.get();
            } catch (RuntimeException e) {
                throw e;
            } catch (Exception e) {
                throw new IOException("Supplier failed", e);
            }
            writeObject(file, computed);
            return computed;
        }
    }

    public <T extends Serializable> T get(String key, Class<T> type) throws IOException, ClassNotFoundException {
        String k = Objects.requireNonNull(key, "key");
        synchronized (lockForKeyHash(k)) {
            Path file = pathForKey(k);
            if (!Files.isRegularFile(file)) {
                return null;
            }
            return readObject(file, type);
        }
    }

    public <T extends Serializable> void put(String key, T value) throws IOException {
        Objects.requireNonNull(value, "value");
        synchronized (lockForKeyHash(Objects.requireNonNull(key, "key"))) {
            writeObject(pathForKey(key), value);
        }
    }

    public boolean invalidate(String key) throws IOException {
        synchronized (lockForKeyHash(Objects.requireNonNull(key, "key"))) {
            return Files.deleteIfExists(pathForKey(key));
        }
    }

    public void clear() throws IOException {
        if (!Files.isDirectory(cacheDir)) {
            return;
        }
        try (var stream = Files.list(cacheDir)) {
            java.util.List<Path> paths = stream
                    .filter(p -> Files.isRegularFile(p) && p.getFileName().toString().endsWith(".ser"))
                    .toList();
            for (Path p : paths) {
                String name = p.getFileName().toString();
                String hashKey = name.substring(0, name.length() - 4);
                synchronized (keyLocks.computeIfAbsent(hashKey, k -> new Object())) {
                    Files.deleteIfExists(p);
                }
            }
        }
    }

    private Object lockForKeyHash(String logicalKey) {
        String hashKey = sha256Hex(logicalKey);
        return keyLocks.computeIfAbsent(hashKey, k -> new Object());
    }

    private Path pathForKey(String key) {
        return cacheDir.resolve(sha256Hex(key) + ".ser");
    }

    private static String sha256Hex(String input) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] digest = md.digest(input.getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder(digest.length * 2);
            for (byte b : digest) {
                sb.append(String.format("%02x", b & 0xff));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    @SuppressWarnings("unchecked")
    private static <T extends Serializable> T readObject(Path file, Class<T> type)
            throws IOException, ClassNotFoundException {
        try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(Files.newInputStream(file)))) {
            Object obj = ois.readObject();
            if (!type.isInstance(obj)) {
                throw new ClassCastException("Expected " + type.getName() + " but got " + obj.getClass().getName());
            }
            return (T) obj;
        }
    }

    private static void writeObject(Path file, Serializable value) throws IOException {
        Path parent = file.getParent();
        if (parent != null) {
            Files.createDirectories(parent);
        }
        Path tmp = file.resolveSibling(file.getFileName().toString() + ".tmp");
        try (ObjectOutputStream oos = new ObjectOutputStream(new BufferedOutputStream(Files.newOutputStream(tmp)))) {
            oos.writeObject(value);
        }
        Files.move(tmp, file, java.nio.file.StandardCopyOption.REPLACE_EXISTING, java.nio.file.StandardCopyOption.ATOMIC_MOVE);
    }

    @FunctionalInterface
    public interface SerializableSupplier<T extends Serializable> {
        T get() throws Exception;
    }

    public static final class UserPreferences implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String userId;
        private final Map<String, String> settings;
        private final String theme;
        private final boolean notificationsEnabled;

        public UserPreferences(String userId, Map<String, String> settings, String theme, boolean notificationsEnabled) {
            this.userId = userId;
            this.settings = new HashMap<>(settings);
            this.theme = theme;
            this.notificationsEnabled = notificationsEnabled;
        }

        public String getUserId() {
            return userId;
        }

        public Map<String, String> getSettings() {
            return new HashMap<>(settings);
        }

        public String getTheme() {
            return theme;
        }

        public boolean isNotificationsEnabled() {
            return notificationsEnabled;
        }
    }

    public static final class SessionData implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String sessionId;
        private final String userId;
        private final long createdAtMillis;
        private final Map<String, Serializable> attributes;

        public SessionData(String sessionId, String userId, long createdAtMillis, Map<String, Serializable> attributes) {
            this.sessionId = sessionId;
            this.userId = userId;
            this.createdAtMillis = createdAtMillis;
            this.attributes = new HashMap<>(attributes);
        }

        public String getSessionId() {
            return sessionId;
        }

        public String getUserId() {
            return userId;
        }

        public long getCreatedAtMillis() {
            return createdAtMillis;
        }

        public Map<String, Serializable> getAttributes() {
            return new HashMap<>(attributes);
        }
    }

    public static void main(String[] args) throws Exception {
        Path dir = Path.of(System.getProperty("java.io.tmpdir"), "disk-object-cache-demo");
        DiskObjectCache cache = new DiskObjectCache(dir);

        UserPreferences prefs = cache.getOrCompute(
                "user:42:prefs",
                UserPreferences.class,
                () -> expensiveUserPreferences("42"));

        SessionData session = cache.getOrCompute(
                "session:abc123",
                SessionData.class,
                () -> expensiveSession("abc123", "42"));

        System.out.println(prefs.getTheme() + " " + prefs.getSettings().get("locale"));
        System.out.println(session.getSessionId() + " " + session.getAttributes().get("cartId"));
    }

    private static UserPreferences expensiveUserPreferences(String userId) {
        Map<String, String> s = new HashMap<>();
        s.put("locale", "en-US");
        s.put("timezone", "America/New_York");
        return new UserPreferences(userId, s, "dark", true);
    }

    private static SessionData expensiveSession(String sessionId, String userId) {
        Map<String, Serializable> attrs = new HashMap<>();
        attrs.put("cartId", "cart-999");
        attrs.put("role", "user");
        return new SessionData(sessionId, userId, System.currentTimeMillis(), attrs);
    }
}
