using System.Runtime.Serialization.Formatters.Binary;

namespace SessionManagement;

internal static class Program
{
    private static void Main(string[] args)
    {
        var baseDir = Path.Combine(AppContext.BaseDirectory, "sessions");
        var manager = new SessionManager(baseDir);

        var session = new UserSession
        {
            UserId = "user-42",
            Preferences = new UserPreferences { Theme = "dark", Language = "en-US" },
            ShoppingCart = new ShoppingCart
            {
                Items =
                {
                    new CartItem { ProductId = "sku-1", Quantity = 2, UnitPrice = 9.99m },
                    new CartItem { ProductId = "sku-7", Quantity = 1, UnitPrice = 24.50m }
                }
            },
            Permissions = new CustomPermissions()
        };

        session.Permissions.Grant("orders.read");
        session.Permissions.Grant("orders.write");

        manager.SaveSession(session);

        var loaded = manager.LoadSession(session.UserId);
        if (loaded is null)
        {
            Console.WriteLine("Failed to load session.");
            return;
        }

        Console.WriteLine(loaded.UserId);
        Console.WriteLine(loaded.Preferences.Theme);
        Console.WriteLine(loaded.ShoppingCart.Items.Count);
        Console.WriteLine(loaded.Permissions.Can("orders.read"));
        Console.WriteLine(loaded.Permissions.Can("admin"));
    }
}

[Serializable]
public sealed class UserSession
{
    public string UserId { get; set; } = string.Empty;
    public UserPreferences Preferences { get; set; } = new();
    public ShoppingCart ShoppingCart { get; set; } = new();
    public CustomPermissions Permissions { get; set; } = new();
}

[Serializable]
public sealed class UserPreferences
{
    public string Theme { get; set; } = "light";
    public string Language { get; set; } = "en";
}

[Serializable]
public sealed class ShoppingCart
{
    public List<CartItem> Items { get; set; } = new();
}

[Serializable]
public sealed class CartItem
{
    public string ProductId { get; set; } = string.Empty;
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
}

[Serializable]
public sealed class CustomPermissions
{
    private readonly List<string> _grants = new();

    public IReadOnlyCollection<string> Grants => _grants;

    public void Grant(string permission)
    {
        if (string.IsNullOrWhiteSpace(permission))
            return;
        var p = permission.Trim();
        if (_grants.Any(x => string.Equals(x, p, StringComparison.OrdinalIgnoreCase)))
            return;
        _grants.Add(p);
    }

    public void Revoke(string permission)
    {
        if (string.IsNullOrWhiteSpace(permission))
            return;
        var p = permission.Trim();
        for (var i = _grants.Count - 1; i >= 0; i--)
        {
            if (string.Equals(_grants[i], p, StringComparison.OrdinalIgnoreCase))
                _grants.RemoveAt(i);
        }
    }

    public bool Can(string permission)
    {
        if (string.IsNullOrWhiteSpace(permission))
            return false;
        var p = permission.Trim();
        return _grants.Any(x => string.Equals(x, p, StringComparison.OrdinalIgnoreCase));
    }

    public bool CanAny(IEnumerable<string> permissions)
    {
        foreach (var p in permissions)
        {
            if (Can(p))
                return true;
        }
        return false;
    }

    public bool CanAll(IEnumerable<string> permissions)
    {
        foreach (var p in permissions)
        {
            if (!Can(p))
                return false;
        }
        return true;
    }
}

public sealed class SessionManager
{
    private readonly string _rootDirectory;
    private static readonly BinaryFormatter Formatter = new();

    public SessionManager(string rootDirectory)
    {
        _rootDirectory = rootDirectory;
        Directory.CreateDirectory(_rootDirectory);
    }

    public void SaveSession(UserSession session)
    {
        ArgumentNullException.ThrowIfNull(session);
        if (string.IsNullOrWhiteSpace(session.UserId))
            throw new ArgumentException("UserId is required.", nameof(session));

        var path = GetSessionPath(session.UserId);
        using var stream = File.Create(path);
        Formatter.Serialize(stream, session);
    }

    public UserSession? LoadSession(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
            throw new ArgumentException("UserId is required.", nameof(userId));

        var path = GetSessionPath(userId);
        if (!File.Exists(path))
            return null;

        using var stream = File.OpenRead(path);
        var obj = Formatter.Deserialize(stream);
        return obj as UserSession;
    }

    public bool DeleteSession(string userId)
    {
        if (string.IsNullOrWhiteSpace(userId))
            throw new ArgumentException("UserId is required.", nameof(userId));

        var path = GetSessionPath(userId);
        if (!File.Exists(path))
            return false;

        File.Delete(path);
        return true;
    }

    private string GetSessionPath(string userId)
    {
        var safe = SanitizeFileName(userId);
        return Path.Combine(_rootDirectory, safe + ".session");
    }

    private static string SanitizeFileName(string userId)
    {
        foreach (var c in Path.GetInvalidFileNameChars())
            userId = userId.Replace(c, '_');
        return userId;
    }
}
