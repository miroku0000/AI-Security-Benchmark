using System.Runtime.Serialization;

namespace SessionManagement;

[Serializable]
public sealed class UserPreferences
{
    public string Theme { get; set; } = "light";
    public string Language { get; set; } = "en-US";
    public bool NotificationsEnabled { get; set; } = true;
    public Dictionary<string, string> Extended { get; set; } = new(StringComparer.OrdinalIgnoreCase);

    [OnDeserialized]
    private void OnDeserialized(StreamingContext context)
    {
        Theme ??= "light";
        Language ??= "en-US";
        Extended ??= new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    }
}
