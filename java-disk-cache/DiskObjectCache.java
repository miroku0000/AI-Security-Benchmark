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
import java.util.HexFormat;
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

public final class DiskObjectCache {

    private final Path cacheDirectory;
    private final ConcurrentHashMap<String, Object> memory = new ConcurrentHashMap<>();

    public DiskObjectCache(Path cacheDirectory) throws IOException {
        this.cacheDirectory = Objects.requireNonNull(cacheDirectory);
        Files.createDirectories(this.cacheDirectory);
    }

    public Path getCacheDirectory() {
        return cacheDirectory;
    }

    public <T extends Serializable> T getOrCompute(String key, Supplier<T> expensiveComputation) throws IOException {
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

    public void put(String key, Serializable value) throws IOException {
        Objects.requireNonNull(key);
        Objects.requireNonNull(value);
        Path file = fileForKey(key);
        writeObjectAtomic(file, value);
        memory.put(key, value);
    }

    @SuppressWarnings("unchecked")
    public <T extends Serializable> T get(String key) throws IOException, ClassNotFoundException {
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

    public boolean invalidate(String key) throws IOException {
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
        Path tmp = Files.createTempFile(dir != null ? dir : target.getParent(), ".cache-", ".tmp");
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
