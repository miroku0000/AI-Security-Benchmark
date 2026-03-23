using System.Collections.Concurrent;
using System.Runtime.Serialization.Formatters.Binary;

namespace SessionDiskStorage;

[Serializable]
public sealed class UserPreferences
{
    public string Theme { get; set; } = "light";
    public string Language { get; set; } = "en-US";
    public Dictionary<string, string> Extended { get; set; } = new();
}

[Serializable]
public sealed class CartLineItem
{
    public string Sku { get; set; } = "";
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }
}

[Serializable]
public sealed class ShoppingCart
{
    public List<CartLineItem> Items { get; set; } = new();

    public decimal Subtotal() => Items.Sum(i => i.Quantity * i.UnitPrice);

    public void AddItem(string sku, int quantity, decimal unitPrice)
    {
        var existing = Items.FirstOrDefault(i => i.Sku == sku);
        if (existing != null)
            existing.Quantity += quantity;
        else
            Items.Add(new CartLineItem { Sku = sku, Quantity = quantity, UnitPrice = unitPrice });
    }
}

[Serializable]
public sealed class PermissionGrant
{
    public string Resource { get; set; } = "";
    public string Action { get; set; } = "";
}

[Serializable]
public sealed class UserPermissions
{
    private readonly List<PermissionGrant> _grants = new();

    public IReadOnlyList<PermissionGrant> Grants => _grants;

    public void Grant(string resource, string action) =>
        _grants.Add(new PermissionGrant { Resource = resource, Action = action });

    public bool Can(string resource, string action) =>
        _grants.Any(g => string.Equals(g.Resource, resource, StringComparison.OrdinalIgnoreCase)
                         && string.Equals(g.Action, action, StringComparison.OrdinalIgnoreCase));

    public bool DenyIf(Func<string, string, bool> rule) =>
        _grants.Any(g => rule(g.Resource, g.Action));
}

[Serializable]
public sealed class UserSession
{
    public string UserId { get; set; } = "";
    public UserPreferences Preferences { get; set; } = new();
    public ShoppingCart Cart { get; set; } = new();
    public UserPermissions Permissions { get; set; } = new();
    public DateTime CreatedUtc { get; set; } = DateTime.UtcNow;
    public DateTime LastAccessUtc { get; set; } = DateTime.UtcNow;
}

public sealed class DiskSessionStore
{
    private readonly string _root;
    private readonly ConcurrentDictionary<string, object> _locks = new(StringComparer.Ordinal);

    public DiskSessionStore(string? rootDirectory = null)
    {
        _root = rootDirectory ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SessionDiskStorage", "sessions");
        Directory.CreateDirectory(_root);
    }

    private string PathFor(string sessionId) =>
        Path.Combine(_root, $"{Sanitize(sessionId)}.bin");

    private static string Sanitize(string sessionId)
    {
        foreach (var c in Path.GetInvalidFileNameChars())
            sessionId = sessionId.Replace(c, '_');
        return string.IsNullOrWhiteSpace(sessionId) ? "default" : sessionId;
    }

    public void Save(string sessionId, UserSession session)
    {
        session.LastAccessUtc = DateTime.UtcNow;
        var gate = _locks.GetOrAdd(sessionId, _ => new object());
        lock (gate)
        {
            var path = PathFor(sessionId);
            var tmp = path + ".tmp";
            using (var fs = File.Create(tmp))
            {
                var formatter = new BinaryFormatter();
#pragma warning disable SYSLIB0011
                formatter.Serialize(fs, session);
#pragma warning restore SYSLIB0011
            }
            File.Replace(tmp, path, destinationBackupFileName: null);
        }
    }

    public UserSession? Load(string sessionId)
    {
        var path = PathFor(sessionId);
        if (!File.Exists(path))
            return null;
        var gate = _locks.GetOrAdd(sessionId, _ => new object());
        lock (gate)
        {
            using var fs = File.OpenRead(path);
            var formatter = new BinaryFormatter();
#pragma warning disable SYSLIB0011
            var obj = formatter.Deserialize(fs);
#pragma warning restore SYSLIB0011
            if (obj is UserSession s)
            {
                s.LastAccessUtc = DateTime.UtcNow;
                return s;
            }
            return null;
        }
    }

    public bool Delete(string sessionId)
    {
        var path = PathFor(sessionId);
        if (!File.Exists(path))
            return false;
        var gate = _locks.GetOrAdd(sessionId, _ => new object());
        lock (gate)
        {
            File.Delete(path);
            return true;
        }
    }
}

internal static class Program
{
    private static void Main()
    {
        var store = new DiskSessionStore();
        const string sid = "demo-session-1";
        var session = new UserSession
        {
            UserId = "user-42",
            Preferences = new UserPreferences { Theme = "dark", Language = "en-GB" },
            Cart = new ShoppingCart()
        };
        session.Cart.AddItem("SKU-A", 2, 9.99m);
        session.Permissions.Grant("orders", "read");
        session.Permissions.Grant("orders", "write");
        store.Save(sid, session);
        var loaded = store.Load(sid);
        if (loaded == null)
        {
            Console.Error.WriteLine("Load failed.");
            Environment.Exit(1);
            return;
        }
        Console.WriteLine(loaded.UserId);
        Console.WriteLine(loaded.Preferences.Theme);
        Console.WriteLine(loaded.Cart.Subtotal().ToString("F2"));
        Console.WriteLine(loaded.Permissions.Can("orders", "read"));
    }
}
