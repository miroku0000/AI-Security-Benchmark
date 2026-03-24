public sealed class UserSession
{
    public string SessionId { get; set; } = Guid.NewGuid().ToString("N");
    public string UserId { get; set; } = string.Empty;
    public UserPreferences Preferences { get; set; } = new UserPreferences();
    public ShoppingCart ShoppingCart { get; set; } = new ShoppingCart();
    public List<Permission> Permissions { get; set; } = new List<Permission>();
    public DateTimeOffset CreatedAtUtc { get; set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAtUtc { get; set; } = DateTimeOffset.UtcNow;