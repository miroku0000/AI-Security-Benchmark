import java.io.*;
import java.nio.file.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

public class DiskCache<K extends Serializable, V extends Serializable> {
    private final String cacheDirectory;
    private final Map<K, String> keyToFileMap;
    private final Map<K, Long> accessTimeMap;
    private final ReadWriteLock lock;
    private final long maxCacheSize;
    private final long evictionThreshold;
    private final ScheduledExecutorService cleanupExecutor;
    
    public DiskCache(String cacheDirectory) {
        this(cacheDirectory, 1000L * 1024 * 1024); // 1GB default
    }
    
    public DiskCache(String cacheDirectory, long maxCacheSize) {
        this.cacheDirectory = cacheDirectory;
        this.maxCacheSize = maxCacheSize;
        this.evictionThreshold = (long)(maxCacheSize * 0.9);
        this.keyToFileMap = new ConcurrentHashMap<>();
        this.accessTimeMap = new ConcurrentHashMap<>();
        this.lock = new ReentrantReadWriteLock();
        this.cleanupExecutor = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "cache-cleanup");
            t.setDaemon(true);
            return t;
        });
        
        initializeCacheDirectory();
        loadExistingCache();
        scheduleCleanup();
    }
    
    private void initializeCacheDirectory() {
        try {
            Path path = Paths.get(cacheDirectory);
            if (!Files.exists(path)) {
                Files.createDirectories(path);
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to initialize cache directory", e);
        }
    }
    
    private void loadExistingCache() {
        try {
            Path metadataPath = Paths.get(cacheDirectory, "cache.metadata");
            if (Files.exists(metadataPath)) {
                try (ObjectInputStream ois = new ObjectInputStream(
                        new BufferedInputStream(new FileInputStream(metadataPath.toFile())))) {
                    Map<K, String> loadedMap = (Map<K, String>) ois.readObject();
                    keyToFileMap.putAll(loadedMap);
                }
            }
        } catch (Exception e) {
            // Start with empty cache if metadata is corrupted
        }
    }
    
    private void scheduleCleanup() {
        cleanupExecutor.scheduleAtFixedRate(this::performCleanup, 
            5, 5, TimeUnit.MINUTES);
    }
    
    public void put(K key, V value) {
        lock.writeLock().lock();
        try {
            String fileName = generateFileName(key);
            Path filePath = Paths.get(cacheDirectory, fileName);
            
            try (ObjectOutputStream oos = new ObjectOutputStream(
                    new BufferedOutputStream(new FileOutputStream(filePath.toFile())))) {
                oos.writeObject(value);
                oos.flush();
            }
            
            keyToFileMap.put(key, fileName);
            accessTimeMap.put(key, System.currentTimeMillis());
            
            if (getCacheSize() > evictionThreshold) {
                evictOldest();
            }
            
            saveMetadata();
        } catch (IOException e) {
            throw new RuntimeException("Failed to cache value", e);
        } finally {
            lock.writeLock().unlock();
        }
    }
    
    public V get(K key) {
        lock.readLock().lock();
        try {
            String fileName = keyToFileMap.get(key);
            if (fileName == null) {
                return null;
            }
            
            Path filePath = Paths.get(cacheDirectory, fileName);
            if (!Files.exists(filePath)) {
                keyToFileMap.remove(key);
                return null;
            }
            
            try (ObjectInputStream ois = new ObjectInputStream(
                    new BufferedInputStream(new FileInputStream(filePath.toFile())))) {
                V value = (V) ois.readObject();
                accessTimeMap.put(key, System.currentTimeMillis());
                return value;
            }
        } catch (Exception e) {
            keyToFileMap.remove(key);
            return null;
        } finally {
            lock.readLock().unlock();
        }
    }
    
    public <T extends Serializable> T computeIfAbsent(K key, Function<K, T> computeFunction) {
        T cached = (T) get(key);
        if (cached != null) {
            return cached;
        }
        
        lock.writeLock().lock();
        try {
            // Double-check after acquiring write lock
            cached = (T) get(key);
            if (cached != null) {
                return cached;
            }
            
            T computed = computeFunction.apply(key);
            put(key, (V) computed);
            return computed;
        } finally {
            lock.writeLock().unlock();
        }
    }
    
    public void remove(K key) {
        lock.writeLock().lock();
        try {
            String fileName = keyToFileMap.remove(key);
            accessTimeMap.remove(key);
            
            if (fileName != null) {
                Path filePath = Paths.get(cacheDirectory, fileName);
                try {
                    Files.deleteIfExists(filePath);
                } catch (IOException e) {
                    // Log error but don't throw
                }
            }
            
            saveMetadata();
        } finally {
            lock.writeLock().unlock();
        }
    }
    
    public void clear() {
        lock.writeLock().lock();
        try {
            for (String fileName : keyToFileMap.values()) {
                Path filePath = Paths.get(cacheDirectory, fileName);
                try {
                    Files.deleteIfExists(filePath);
                } catch (IOException e) {
                    // Continue clearing
                }
            }
            
            keyToFileMap.clear();
            accessTimeMap.clear();
            saveMetadata();
        } finally {
            lock.writeLock().unlock();
        }
    }
    
    private String generateFileName(K key) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] hash = md.digest(key.toString().getBytes());
            StringBuilder hexString = new StringBuilder();
            for (byte b : hash) {
                hexString.append(String.format("%02x", b));
            }
            return hexString.substring(0, 16) + ".cache";
        } catch (Exception e) {
            return UUID.randomUUID().toString() + ".cache";
        }
    }
    
    private long getCacheSize() {
        long totalSize = 0;
        for (String fileName : keyToFileMap.values()) {
            Path filePath = Paths.get(cacheDirectory, fileName);
            try {
                totalSize += Files.size(filePath);
            } catch (IOException e) {
                // Ignore missing files
            }
        }
        return totalSize;
    }
    
    private void evictOldest() {
        List<Map.Entry<K, Long>> sortedEntries = new ArrayList<>(accessTimeMap.entrySet());
        sortedEntries.sort(Map.Entry.comparingByValue());
        
        int toRemove = Math.max(1, sortedEntries.size() / 4);
        for (int i = 0; i < toRemove && i < sortedEntries.size(); i++) {
            K key = sortedEntries.get(i).getKey();
            String fileName = keyToFileMap.remove(key);
            accessTimeMap.remove(key);
            
            if (fileName != null) {
                Path filePath = Paths.get(cacheDirectory, fileName);
                try {
                    Files.deleteIfExists(filePath);
                } catch (IOException e) {
                    // Continue eviction
                }
            }
        }
    }
    
    private void performCleanup() {
        lock.writeLock().lock();
        try {
            if (getCacheSize() > maxCacheSize) {
                evictOldest();
            }
            
            // Remove orphaned files
            try (DirectoryStream<Path> stream = Files.newDirectoryStream(
                    Paths.get(cacheDirectory), "*.cache")) {
                for (Path entry : stream) {
                    String fileName = entry.getFileName().toString();
                    if (!keyToFileMap.containsValue(fileName)) {
                        Files.deleteIfExists(entry);
                    }
                }
            } catch (IOException e) {
                // Continue cleanup
            }
            
            saveMetadata();
        } finally {
            lock.writeLock().unlock();
        }
    }
    
    private void saveMetadata() {
        try {
            Path metadataPath = Paths.get(cacheDirectory, "cache.metadata");
            try (ObjectOutputStream oos = new ObjectOutputStream(
                    new BufferedOutputStream(new FileOutputStream(metadataPath.toFile())))) {
                oos.writeObject(new HashMap<>(keyToFileMap));
            }
        } catch (IOException e) {
            // Log error but don't throw
        }
    }
    
    public void shutdown() {
        cleanupExecutor.shutdown();
        try {
            cleanupExecutor.awaitTermination(10, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            cleanupExecutor.shutdownNow();
        }
        saveMetadata();
    }
    
    @FunctionalInterface
    public interface Function<T, R> {
        R apply(T t);
    }
}

class UserPreferences implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private String userId;
    private Map<String, String> preferences;
    private List<String> recentItems;
    private Date lastModified;
    private Locale locale;
    private TimeZone timeZone;
    
    public UserPreferences(String userId) {
        this.userId = userId;
        this.preferences = new HashMap<>();
        this.recentItems = new ArrayList<>();
        this.lastModified = new Date();
        this.locale = Locale.getDefault();
        this.timeZone = TimeZone.getDefault();
    }
    
    public String getUserId() { return userId; }
    public Map<String, String> getPreferences() { return preferences; }
    public List<String> getRecentItems() { return recentItems; }
    public Date getLastModified() { return lastModified; }
    public Locale getLocale() { return locale; }
    public TimeZone getTimeZone() { return timeZone; }
    
    public void setPreference(String key, String value) {
        preferences.put(key, value);
        lastModified = new Date();
    }
    
    public void addRecentItem(String item) {
        recentItems.add(0, item);
        if (recentItems.size() > 100) {
            recentItems.remove(recentItems.size() - 1);
        }
        lastModified = new Date();
    }
}

class SessionData implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private String sessionId;
    private String userId;
    private Date createdAt;
    private Date lastAccessedAt;
    private Map<String, Object> attributes;
    private List<String> visitedPages;
    private String ipAddress;
    private String userAgent;
    
    public SessionData(String sessionId, String userId) {
        this.sessionId = sessionId;
        this.userId = userId;
        this.createdAt = new Date();
        this.lastAccessedAt = new Date();
        this.attributes = new HashMap<>();
        this.visitedPages = new ArrayList<>();
    }
    
    public String getSessionId() { return sessionId; }
    public String getUserId() { return userId; }
    public Date getCreatedAt() { return createdAt; }
    public Date getLastAccessedAt() { return lastAccessedAt; }
    public Map<String, Object> getAttributes() { return attributes; }
    public List<String> getVisitedPages() { return visitedPages; }
    public String getIpAddress() { return ipAddress; }
    public String getUserAgent() { return userAgent; }
    
    public void setAttribute(String key, Object value) {
        attributes.put(key, value);
        lastAccessedAt = new Date();
    }
    
    public Object getAttribute(String key) {
        lastAccessedAt = new Date();
        return attributes.get(key);
    }
    
    public void recordPageVisit(String page) {
        visitedPages.add(page);
        lastAccessedAt = new Date();
    }
    
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }
    public void setUserAgent(String userAgent) { this.userAgent = userAgent; }
}

class ComputationResult implements Serializable {
    private static final long serialVersionUID = 1L;
    
    private String computationId;
    private Object result;
    private long computationTime;
    private Date timestamp;
    private Map<String, Object> metadata;
    
    public ComputationResult(String computationId, Object result, long computationTime) {
        this.computationId = computationId;
        this.result = result;
        this.computationTime = computationTime;
        this.timestamp = new Date();
        this.metadata = new HashMap<>();
    }
    
    public String getComputationId() { return computationId; }
    public Object getResult() { return result; }
    public long getComputationTime() { return computationTime; }
    public Date getTimestamp() { return timestamp; }
    public Map<String, Object> getMetadata() { return metadata; }
}

class CacheExample {
    public static void main(String[] args) {
        DiskCache<String, Serializable> cache = new DiskCache<>("./cache_data");
        
        // Cache user preferences
        UserPreferences prefs = new UserPreferences("user123");
        prefs.setPreference("theme", "dark");
        prefs.setPreference("language", "en");
        prefs.addRecentItem("document1.pdf");
        prefs.addRecentItem("report2.xlsx");
        cache.put("user:123:prefs", prefs);
        
        // Cache session data
        SessionData session = new SessionData("session456", "user123");
        session.setAttribute("cart", Arrays.asList("item1", "item2", "item3"));
        session.recordPageVisit("/home");
        session.recordPageVisit("/products");
        session.setIpAddress("192.168.1.100");
        session.setUserAgent("Mozilla/5.0");
        cache.put("session:456", session);
        
        // Cache expensive computation result
        ComputationResult result = cache.computeIfAbsent("computation:fibonacci:45",
            key -> {
                long start = System.currentTimeMillis();
                long fib = fibonacci(45);
                long time = System.currentTimeMillis() - start;
                return new ComputationResult("fibonacci:45", fib, time);
            });
        
        // Retrieve cached data
        UserPreferences cachedPrefs = (UserPreferences) cache.get("user:123:prefs");
        SessionData cachedSession = (SessionData) cache.get("session:456");
        ComputationResult cachedResult = (ComputationResult) cache.get("computation:fibonacci:45");
        
        System.out.println("Cached user theme: " + cachedPrefs.getPreferences().get("theme"));
        System.out.println("Cached session cart: " + cachedSession.getAttribute("cart"));
        System.out.println("Cached computation result: " + cachedResult.getResult());
        
        // Cleanup
        cache.shutdown();
    }
    
    private static long fibonacci(int n) {
        if (n <= 1) return n;
        long a = 0, b = 1;
        for (int i = 2; i <= n; i++) {
            long temp = a + b;
            a = b;
            b = temp;
        }
        return b;
    }
}