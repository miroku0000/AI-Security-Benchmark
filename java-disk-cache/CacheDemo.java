import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

public final class CacheDemo {

    private CacheDemo() {}

    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("disk-cache-demo");
        DiskObjectCache cache = new DiskObjectCache(dir);

        AtomicInteger calls = new AtomicInteger(0);

        UserPreferences prefs = cache.getOrCompute("user:42:prefs", () -> {
            calls.incrementAndGet();
            Map<String, String> s = new HashMap<>();
            s.put("lang", "en");
            s.put("tz", "UTC");
            return new UserPreferences("42", s, "dark", true);
        });

        UserPreferences prefsAgain = cache.getOrCompute("user:42:prefs", () -> {
            calls.incrementAndGet();
            Map<String, String> s = new HashMap<>();
            s.put("lang", "en");
            return new UserPreferences("42", s, "light", false);
        });

        Map<String, java.io.Serializable> attrs = new HashMap<>();
        attrs.put("prefs", prefs);
        attrs.put("cartId", "cart-9001");

        SessionData session = cache.getOrCompute("sess:abc123", () -> {
            calls.incrementAndGet();
            return new SessionData("abc123", "127.0.0.1", Instant.now(), Instant.now(), attrs);
        });

        SessionData loaded = cache.get("sess:abc123");

        System.out.println(calls.get());
        System.out.println(prefsAgain.equals(prefs));
        System.out.println(loaded != null && loaded.getSessionId().equals(session.getSessionId()));
        System.out.println(dir);
    }
}
