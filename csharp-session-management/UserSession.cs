using System.Runtime.Serialization;

namespace SessionManagement;

[Serializable]
public sealed class UserSession
{
    public string SessionId { get; set; } = Guid.NewGuid().ToString("N");
    public string UserId { get; set; } = string.Empty;
    public DateTime CreatedUtc { get; set; } = DateTime.UtcNow;
    public DateTime LastAccessUtc { get; set; } = DateTime.UtcNow;
    public UserPreferences Preferences { get; set; } = new();
    public ShoppingCart Cart { get; set; } = new();
    public List<Permission> Permissions { get; set; } = new();

    public void Touch()
    {
        LastAccessUtc = DateTime.UtcNow;
    }

    public bool HasPermission(string resource, bool writeOperation)
    {
        foreach (var p in Permissions)
        {
            if (p.CanAccess(resource, writeOperation))
                return true;
        }
        return false;
    }

    [OnDeserialized]
    private void OnDeserialized(StreamingContext context)
    {
        SessionId ??= Guid.NewGuid().ToString("N");
        UserId ??= string.Empty;
        Preferences ??= new UserPreferences();
        Cart ??= new ShoppingCart();
        Permissions ??= new List<Permission>();
    }
}
