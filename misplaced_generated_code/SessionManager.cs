using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

public class Permission
{
    public string Resource { get; set; } = string.Empty;
    public bool CanRead { get; set; }
    public bool CanWrite { get; set; }
    public bool CanDelete { get; set; }

    public bool IsAllowed(string action) => action switch
    {
        "read" => CanRead,
        "write" => CanWrite,
        "delete" => CanDelete,
        _ => false
    };
}

public class CartItem
{
    public string ProductId { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public int Quantity { get; set; }
    public decimal Price { get; set; }
    public decimal Total => Quantity * Price;
}

public class UserPreferences
{
    public string Theme { get; set; } = "light";
    public string Language { get; set; } = "en";
    public string Currency { get; set; } = "USD";
    public bool NotificationsEnabled { get; set; } = true;
}

public class UserSession
{
    public string SessionId { get; set; } = Guid.NewGuid().ToString();
    public string UserId { get; set; } = string.Empty;
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime LastAccessedAt { get; set; } = DateTime.UtcNow;
    public UserPreferences Preferences { get; set; } = new();
    public List<CartItem> ShoppingCart { get; set; } = new();
    public List<Permission> Permissions { get; set; } = new();

    public void AddToCart(string productId, string name, int quantity, decimal price)
    {
        ShoppingCart.Add(new CartItem
        {
            ProductId = productId,
            Name = name,
            Quantity = quantity,
            Price = price
        });
        Touch();
    }

    public void Touch() => LastAccessedAt = DateTime.UtcNow;
}

public class SessionManager
{
    private readonly string _sessionDirectory;
    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase
    };

    public SessionManager(string sessionDirectory = "sessions")
    {
        _sessionDirectory = sessionDirectory;
        Directory.CreateDirectory(_sessionDirectory);
    }

    public void SaveSession(UserSession session)
    {
        var filePath = GetSessionPath(session.SessionId);
        var json = JsonSerializer.Serialize(session, _jsonOptions);
        File.WriteAllText(filePath, json);
    }

    public UserSession? LoadSession(string sessionId)
    {
        var filePath = GetSessionPath(sessionId);
        if (!File.Exists(filePath))
            return null;

        var json = File.ReadAllText(filePath);
        var session = JsonSerializer.Deserialize<UserSession>(json, _jsonOptions);
        session?.Touch();
        return session;
    }

    public void DeleteSession(string sessionId)
    {
        var filePath = GetSessionPath(sessionId);
        if (File.Exists(filePath))
            File.Delete(filePath);
    }

    public void CleanExpiredSessions(TimeSpan maxAge)
    {
        foreach (var file in Directory.GetFiles(_sessionDirectory, "*.json"))
        {
            var json = File.ReadAllText(file);
            var session = JsonSerializer.Deserialize<UserSession>(json, _jsonOptions);
            if (session != null && DateTime.UtcNow - session.LastAccessedAt > maxAge)
                File.Delete(file);
        }
    }

    private string GetSessionPath(string sessionId) =>
        Path.Combine(_sessionDirectory, $"{sessionId}.json");
}

public class Program
{
    public static void Main()
    {
        var manager = new SessionManager();

        var session = new UserSession
        {
            UserId = "user-42",
            Preferences = new UserPreferences
            {
                Theme = "dark",
                Language = "en",
                Currency = "EUR",
                NotificationsEnabled = true
            },
            Permissions = new List<Permission>
            {
                new() { Resource = "orders", CanRead = true, CanWrite = true, CanDelete = false },
                new() { Resource = "admin", CanRead = false, CanWrite = false, CanDelete = false }
            }
        };

        session.AddToCart("SKU-101", "Mechanical Keyboard", 1, 89.99m);
        session.AddToCart("SKU-202", "USB-C Cable", 3, 12.50m);

        manager.SaveSession(session);
        Console.WriteLine($"Saved session {session.SessionId}");

        var loaded = manager.LoadSession(session.SessionId);
        if (loaded != null)
        {
            Console.WriteLine($"Loaded session for user: {loaded.UserId}");
            Console.WriteLine($"Theme: {loaded.Preferences.Theme}");
            Console.WriteLine($"Cart items: {loaded.ShoppingCart.Count}");
            foreach (var item in loaded.ShoppingCart)
                Console.WriteLine($"  {item.Name} x{item.Quantity} = {item.Total:C}");
            foreach (var perm in loaded.Permissions)
                Console.WriteLine($"  {perm.Resource}: read={perm.IsAllowed("read")}, write={perm.IsAllowed("write")}");
        }

        manager.DeleteSession(session.SessionId);
        Console.WriteLine("Session cleaned up.");
    }
}
