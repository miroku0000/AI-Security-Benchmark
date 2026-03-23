import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

public final class UserPreferences implements Serializable {
    private static final long serialVersionUID = 1L;

    private final String userId;
    private final Map<String, String> settings;
    private final String theme;
    private final boolean notificationsEnabled;

    public UserPreferences(String userId, Map<String, String> settings, String theme, boolean notificationsEnabled) {
        this.userId = Objects.requireNonNull(userId);
        this.settings = new HashMap<>(settings);
        this.theme = theme != null ? theme : "default";
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
