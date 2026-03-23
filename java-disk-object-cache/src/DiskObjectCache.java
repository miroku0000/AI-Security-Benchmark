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
import java.util.Objects;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

public final class DiskObjectCache<K extends Serializable, V extends Serializable> {

    private final Path rootDir;
    private final ConcurrentHashMap<K, V> memory = new ConcurrentHashMap<>();

    public DiskObjectCache(Path rootDir) throws IOException {
        this.rootDir = Objects.requireNonNull(rootDir, "rootDir");
        Files.createDirectories(this.rootDir);
    }

    public V get(K key) throws IOException, ClassNotFoundException {
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

    public void put(K key, V value) throws IOException {
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

    public V computeIfAbsent(K key, Supplier<? extends V> expensive) throws IOException, ClassNotFoundException {
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

    public void invalidate(K key) throws IOException {
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
