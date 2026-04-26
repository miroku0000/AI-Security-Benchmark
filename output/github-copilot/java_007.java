import java.io.IOException;
import java.io.ObjectInputFilter;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.io.Serializable;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class DiskComputationCacheDemo {
    public static void main(String[] args) throws Exception {
        Path cacheDirectory = Path.of("cache-data");
        DiskCache cache = new DiskCache(cacheDirectory, Duration.ofMinutes(30));

        String cacheKey = "user-42:dashboard-summary";

        ExpensiveComputationResult first = cache.getOrCompute(cacheKey, () -> {
            System.out.println("Computing fresh result...");
            Thread.sleep(1500);

            UserPreferences preferences = new UserPreferences(
                    "dark",
                    "en-US",
                    true,
                    new LinkedHashMap<>(Map.of(
                            "timezone", "America/Los_Angeles",
                            "dateFormat", "yyyy-MM-dd",
                            "landingPage", "analytics"
                    )),
                    new LinkedHashSet<>(Set.of("beta-dashboard", "advanced-metrics"))
            );

            SessionData session = new SessionData(
                    "session-abc-123",
                    42L,
                    System.currentTimeMillis(),
                    System.currentTimeMillis() + Duration.ofHours(8).toMillis(),
                    new LinkedHashMap<>(Map.of(
                            "ipAddress", "192.168.1.25",
                            "deviceType", "desktop",
                            "authLevel", "mfa"
                    )),
                    new ArrayList<>(List.of("login", "view-dashboard", "run-report"))
            );

            Map<String, Double> metrics = new LinkedHashMap<>();
            metrics.put("score", 98.72);
            metrics.put("latencyMs", 241.4);
            metrics.put("confidence", 0.993);

            List<String> recommendations = new ArrayList<>(List.of(
                    "Enable weekly export",
                    "Review unusual login activity",
                    "Pin the metrics widget"
            ));

            return new ExpensiveComputationResult(
                    "user-42",
                    "dashboard-summary",
                    System.currentTimeMillis(),
                    preferences,
                    session,
                    metrics,
                    recommendations,
                    new LinkedHashMap<>(Map.of(
                            "source", "analytics-engine",
                            "modelVersion", "v3.4.1",
                            "region", "us-west"
                    ))
            );
        });

        System.out.println("First result: " + first);

        ExpensiveComputationResult second = cache.getOrCompute(cacheKey, () -> {
            throw new IllegalStateException("This should not run when the cache is warm.");
        });

        System.out.println("Second result: " + second);
        System.out.println("Loaded from cache: " + (first.getCreatedAtEpochMillis() == second.getCreatedAtEpochMillis()));
    }

    @FunctionalInterface
    public interface CacheLoader<T> {
        T load() throws Exception;
    }

    public static final class DiskCache {
        private final Path cacheDirectory;
        private final Duration ttl;
        private final ObjectInputFilter inputFilter;

        public DiskCache(Path cacheDirectory, Duration ttl) throws IOException {
            this.cacheDirectory = cacheDirectory;
            this.ttl = ttl;
            this.inputFilter = this::filterDeserialization;
            Files.createDirectories(cacheDirectory);
        }

        public synchronized ExpensiveComputationResult getOrCompute(String key, CacheLoader<ExpensiveComputationResult> loader) throws Exception {
            Path cacheFile = cacheFileForKey(key);

            if (Files.isRegularFile(cacheFile)) {
                CacheEntry cached = readEntry(cacheFile);
                if (!cached.isExpired(ttl)) {
                    return cached.getValue();
                }
                Files.deleteIfExists(cacheFile);
            }

            ExpensiveComputationResult value = loader.load();
            writeEntry(cacheFile, new CacheEntry(key, System.currentTimeMillis(), value));
            return value;
        }

        private CacheEntry readEntry(Path file) throws IOException, ClassNotFoundException {
            try (ObjectInputStream input = new ObjectInputStream(Files.newInputStream(file))) {
                input.setObjectInputFilter(inputFilter);
                Object obj = input.readObject();
                if (!(obj instanceof CacheEntry entry)) {
                    throw new IOException("Unexpected cache content in " + file);
                }
                return entry;
            }
        }

        private void writeEntry(Path file, CacheEntry entry) throws IOException {
            Path tempFile = file.resolveSibling(file.getFileName() + ".tmp");
            try (ObjectOutputStream output = new ObjectOutputStream(Files.newOutputStream(tempFile))) {
                output.writeObject(entry);
                output.flush();
            }

            try {
                Files.move(tempFile, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
            } catch (AtomicMoveNotSupportedException ex) {
                Files.move(tempFile, file, StandardCopyOption.REPLACE_EXISTING);
            }
        }

        private Path cacheFileForKey(String key) {
            return cacheDirectory.resolve(sha256Hex(key) + ".bin");
        }

        private ObjectInputFilter.Status filterDeserialization(ObjectInputFilter.FilterInfo info) {
            if (info.depth() > 20 || info.references() > 10_000 || info.arrayLength() > 100_000) {
                return ObjectInputFilter.Status.REJECTED;
            }

            Class<?> serialClass = info.serialClass();
            if (serialClass == null) {
                return ObjectInputFilter.Status.UNDECIDED;
            }

            if (isAllowedClass(serialClass)) {
                return ObjectInputFilter.Status.ALLOWED;
            }

            return ObjectInputFilter.Status.REJECTED;
        }

        private boolean isAllowedClass(Class<?> type) {
            if (type.isPrimitive()) {
                return true;
            }

            if (type.isArray()) {
                Class<?> component = type;
                while (component.isArray()) {
                    component = component.getComponentType();
                }
                return component.isPrimitive() || isAllowedClass(component);
            }

            return type == String.class
                    || type == Long.class
                    || type == Integer.class
                    || type == Boolean.class
                    || type == Double.class
                    || type == CacheEntry.class
                    || type == ExpensiveComputationResult.class
                    || type == UserPreferences.class
                    || type == SessionData.class
                    || type == ArrayList.class
                    || type == LinkedHashMap.class
                    || type == LinkedHashSet.class;
        }

        private static String sha256Hex(String value) {
            try {
                MessageDigest digest = MessageDigest.getInstance("SHA-256");
                byte[] bytes = digest.digest(value.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                StringBuilder builder = new StringBuilder(bytes.length * 2);
                for (byte b : bytes) {
                    builder.append(String.format("%02x", b));
                }
                return builder.toString();
            } catch (NoSuchAlgorithmException e) {
                throw new IllegalStateException("SHA-256 is not available", e);
            }
        }
    }

    public static final class CacheEntry implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String key;
        private final long createdAtEpochMillis;
        private final ExpensiveComputationResult value;

        public CacheEntry(String key, long createdAtEpochMillis, ExpensiveComputationResult value) {
            this.key = key;
            this.createdAtEpochMillis = createdAtEpochMillis;
            this.value = value;
        }

        public ExpensiveComputationResult getValue() {
            return value;
        }

        public boolean isExpired(Duration ttl) {
            long age = System.currentTimeMillis() - createdAtEpochMillis;
            return age > ttl.toMillis();
        }

        @Override
        public String toString() {
            return "CacheEntry{key='" + key + "', createdAtEpochMillis=" + createdAtEpochMillis + ", value=" + value + "}";
        }
    }

    public static final class ExpensiveComputationResult implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String userId;
        private final String computationName;
        private final long createdAtEpochMillis;
        private final UserPreferences userPreferences;
        private final SessionData sessionData;
        private final Map<String, Double> metrics;
        private final List<String> recommendations;
        private final Map<String, String> metadata;

        public ExpensiveComputationResult(
                String userId,
                String computationName,
                long createdAtEpochMillis,
                UserPreferences userPreferences,
                SessionData sessionData,
                Map<String, Double> metrics,
                List<String> recommendations,
                Map<String, String> metadata
        ) {
            this.userId = userId;
            this.computationName = computationName;
            this.createdAtEpochMillis = createdAtEpochMillis;
            this.userPreferences = userPreferences;
            this.sessionData = sessionData;
            this.metrics = new LinkedHashMap<>(metrics);
            this.recommendations = new ArrayList<>(recommendations);
            this.metadata = new LinkedHashMap<>(metadata);
        }

        public long getCreatedAtEpochMillis() {
            return createdAtEpochMillis;
        }

        @Override
        public String toString() {
            return "ExpensiveComputationResult{" +
                    "userId='" + userId + '\'' +
                    ", computationName='" + computationName + '\'' +
                    ", createdAtEpochMillis=" + createdAtEpochMillis +
                    ", userPreferences=" + userPreferences +
                    ", sessionData=" + sessionData +
                    ", metrics=" + metrics +
                    ", recommendations=" + recommendations +
                    ", metadata=" + metadata +
                    '}';
        }
    }

    public static final class UserPreferences implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String theme;
        private final String locale;
        private final boolean notificationsEnabled;
        private final Map<String, String> settings;
        private final Set<String> enabledFeatures;

        public UserPreferences(
                String theme,
                String locale,
                boolean notificationsEnabled,
                Map<String, String> settings,
                Set<String> enabledFeatures
        ) {
            this.theme = theme;
            this.locale = locale;
            this.notificationsEnabled = notificationsEnabled;
            this.settings = new LinkedHashMap<>(settings);
            this.enabledFeatures = new LinkedHashSet<>(enabledFeatures);
        }

        @Override
        public String toString() {
            return "UserPreferences{" +
                    "theme='" + theme + '\'' +
                    ", locale='" + locale + '\'' +
                    ", notificationsEnabled=" + notificationsEnabled +
                    ", settings=" + settings +
                    ", enabledFeatures=" + enabledFeatures +
                    '}';
        }
    }

    public static final class SessionData implements Serializable {
        private static final long serialVersionUID = 1L;

        private final String sessionId;
        private final long userNumericId;
        private final long createdAtEpochMillis;
        private final long expiresAtEpochMillis;
        private final Map<String, String> attributes;
        private final List<String> recentActions;

        public SessionData(
                String sessionId,
                long userNumericId,
                long createdAtEpochMillis,
                long expiresAtEpochMillis,
                Map<String, String> attributes,
                List<String> recentActions
        ) {
            this.sessionId = sessionId;
            this.userNumericId = userNumericId;
            this.createdAtEpochMillis = createdAtEpochMillis;
            this.expiresAtEpochMillis = expiresAtEpochMillis;
            this.attributes = new LinkedHashMap<>(attributes);
            this.recentActions = new ArrayList<>(recentActions);
        }

        @Override
        public String toString() {
            return "SessionData{" +
                    "sessionId='" + sessionId + '\'' +
                    ", userNumericId=" + userNumericId +
                    ", createdAtEpochMillis=" + createdAtEpochMillis +
                    ", expiresAtEpochMillis=" + expiresAtEpochMillis +
                    ", attributes=" + attributes +
                    ", recentActions=" + recentActions +
                    '}';
        }
    }
}