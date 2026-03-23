import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class UserPreferences implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String userId;
    private final Map<String, String> settings;

    public UserPreferences(String userId, Map<String, String> settings) {
        this.userId = Objects.requireNonNull(userId, "userId");
        this.settings = new HashMap<>(Objects.requireNonNull(settings, "settings"));
    }

    public String getUserId() {
        return userId;
    }

    public Map<String, String> getSettings() {
        return new HashMap<>(settings);
    }
}
