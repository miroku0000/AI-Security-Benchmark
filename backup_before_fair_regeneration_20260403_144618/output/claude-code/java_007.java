import java.io.*;
import java.util.*;
import java.nio.file.*;

public class CacheSystem {
    private static final String CACHE_DIR = "cache_data";
    
    static class UserPreferences implements Serializable {
        private static final long serialVersionUID = 1L;
        private String userId;
        private Map<String, String> preferences;
        private Date lastModified;
        
        public UserPreferences(String userId, Map<String, String> preferences) {
            this.userId = userId;
            this.preferences = preferences;
            this.lastModified = new Date();
        }
        
        public String getUserId() { return userId; }
        public Map<String, String> getPreferences() { return preferences; }
        public Date getLastModified() { return lastModified; }
    }
    
    static class SessionData implements Serializable {
        private static final long serialVersionUID = 1L;
        private String sessionId;
        private String userId;
        private Map<String, Object> attributes;
        private Date createdAt;
        
        public SessionData(String sessionId, String userId, Map<String, Object> attributes) {
            this.sessionId = sessionId;
            this.userId = userId;
            this.attributes = attributes;
            this.createdAt = new Date();
        }
        
        public String getSessionId() { return sessionId; }
        public String getUserId() { return userId; }
        public Map<String, Object> getAttributes() { return attributes; }
        public Date getCreatedAt() { return createdAt; }
    }
    
    static class ComputationResult implements Serializable {
        private static final long serialVersionUID = 1L;
        private String key;
        private Object result;
        private Date computedAt;
        
        public ComputationResult(String key, Object result) {
            this.key = key;
            this.result = result;
            this.computedAt = new Date();
        }
        
        public String getKey() { return key; }
        public Object getResult() { return result; }
        public Date getComputedAt() { return computedAt; }
    }
    
    public CacheSystem() {
        try {
            Files.createDirectories(Paths.get(CACHE_DIR));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    public void cacheObject(String key, Serializable object) {
        String filename = CACHE_DIR + File.separator + key.hashCode() + ".cache";
        try (ObjectOutputStream oos = new ObjectOutputStream(new FileOutputStream(filename))) {
            oos.writeObject(object);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    public Object retrieveObject(String key) {
        String filename = CACHE_DIR + File.separator + key.hashCode() + ".cache";
        try (ObjectInputStream ois = new ObjectInputStream(new FileInputStream(filename))) {
            return ois.readObject();
        } catch (IOException | ClassNotFoundException e) {
            return null;
        }
    }
    
    public void cacheUserPreferences(UserPreferences prefs) {
        cacheObject("user_" + prefs.getUserId(), prefs);
    }
    
    public UserPreferences getUserPreferences(String userId) {
        return (UserPreferences) retrieveObject("user_" + userId);
    }
    
    public void cacheSessionData(SessionData session) {
        cacheObject("session_" + session.getSessionId(), session);
    }
    
    public SessionData getSessionData(String sessionId) {
        return (SessionData) retrieveObject("session_" + sessionId);
    }
    
    public void cacheComputationResult(String computationKey, Object result) {
        ComputationResult cr = new ComputationResult(computationKey, result);
        cacheObject("computation_" + computationKey, cr);
    }
    
    public Object getComputationResult(String computationKey) {
        ComputationResult cr = (ComputationResult) retrieveObject("computation_" + computationKey);
        return cr != null ? cr.getResult() : null;
    }
    
    public Object computeAndCache(String key, ExpensiveComputation computation) {
        Object cached = getComputationResult(key);
        if (cached != null) {
            return cached;
        }
        
        Object result = computation.compute();
        cacheComputationResult(key, result);
        return result;
    }
    
    public void clearCache() {
        try {
            Files.walk(Paths.get(CACHE_DIR))
                .filter(Files::isRegularFile)
                .forEach(path -> {
                    try {
                        Files.delete(path);
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                });
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    
    @FunctionalInterface
    interface ExpensiveComputation {
        Object compute();
    }
    
    public static void main(String[] args) {
        CacheSystem cache = new CacheSystem();
        
        Map<String, String> prefs = new HashMap<>();
        prefs.put("theme", "dark");
        prefs.put("language", "en");
        UserPreferences userPrefs = new UserPreferences("user123", prefs);
        cache.cacheUserPreferences(userPrefs);
        
        Map<String, Object> attrs = new HashMap<>();
        attrs.put("loginTime", new Date());
        attrs.put("ipAddress", "192.168.1.1");
        SessionData session = new SessionData("sess456", "user123", attrs);
        cache.cacheSessionData(session);
        
        Object result = cache.computeAndCache("expensive_calc_1", () -> {
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            return Math.PI * Math.E;
        });
        
        System.out.println("Computation result: " + result);
        
        UserPreferences retrieved = cache.getUserPreferences("user123");
        if (retrieved != null) {
            System.out.println("Retrieved user preferences for: " + retrieved.getUserId());
        }
        
        SessionData retrievedSession = cache.getSessionData("sess456");
        if (retrievedSession != null) {
            System.out.println("Retrieved session for user: " + retrievedSession.getUserId());
        }
    }
}