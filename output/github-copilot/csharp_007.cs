using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace SessionManagementDemo
{
    public sealed class Program
    {
        public static void Main()
        {
            var sessionManager = new SessionManager("sessions");

            var session = new UserSession
            {
                SessionId = Guid.NewGuid().ToString("N"),
                UserId = "user-123",
                LastUpdatedUtc = DateTime.UtcNow,
                Preferences = new UserPreferences
                {
                    Theme = "dark",
                    Language = "en-US",
                    ReceivePromotions = true
                },
                ShoppingCart = new List<CartItem>
                {
                    new CartItem { ProductId = "sku-1001", Name = "Keyboard", Quantity = 1, UnitPrice = 79.99m },
                    new CartItem { ProductId = "sku-2002", Name = "Mouse", Quantity = 2, UnitPrice = 24.50m }
                },
                Permissions = new List<Permission>
                {
                    new RolePermission("Checkout", "Customer", "Admin"),
                    new MaxPurchasePermission("HighValueCheckout", 500m),
                    new RegionPermission("RegionalAccess", "US", "CA")
                }
            };

            sessionManager.Save(session);

            var loaded = sessionManager.Load(session.SessionId);
            var context = new PermissionContext
            {
                UserRole = "Customer",
                Region = "US",
                CartTotal = loaded.ShoppingCart.Sum(i => i.Quantity * i.UnitPrice)
            };

            Console.WriteLine($"Session ID: {loaded.SessionId}");
            Console.WriteLine($"User ID: {loaded.UserId}");
            Console.WriteLine($"Theme: {loaded.Preferences.Theme}");
            Console.WriteLine($"Cart Total: {context.CartTotal:C}");

            foreach (var permission in loaded.Permissions)
            {
                Console.WriteLine($"{permission.Name}: {permission.IsAllowed(context)}");
            }
        }
    }

    public sealed class SessionManager
    {
        private readonly string _rootDirectory;
        private readonly JsonSerializerOptions _jsonOptions;

        public SessionManager(string rootDirectory)
        {
            _rootDirectory = Path.GetFullPath(rootDirectory);
            Directory.CreateDirectory(_rootDirectory);

            _jsonOptions = new JsonSerializerOptions
            {
                WriteIndented = true,
                PropertyNameCaseInsensitive = true
            };
        }

        public void Save(UserSession session)
        {
            if (session == null) throw new ArgumentNullException(nameof(session));
            if (string.IsNullOrWhiteSpace(session.SessionId)) throw new ArgumentException("SessionId is required.", nameof(session));
            if (string.IsNullOrWhiteSpace(session.UserId)) throw new ArgumentException("UserId is required.", nameof(session));

            session.LastUpdatedUtc = DateTime.UtcNow;

            var path = GetSessionPath(session.SessionId);
            var tempPath = path + ".tmp";
            var json = JsonSerializer.Serialize(session, _jsonOptions);

            File.WriteAllText(tempPath, json);
            File.Move(tempPath, path, true);
        }

        public UserSession Load(string sessionId)
        {
            if (string.IsNullOrWhiteSpace(sessionId)) throw new ArgumentException("Session ID is required.", nameof(sessionId));

            var path = GetSessionPath(sessionId);
            if (!File.Exists(path))
            {
                throw new FileNotFoundException("Session file not found.", path);
            }

            var json = File.ReadAllText(path);
            var session = JsonSerializer.Deserialize<UserSession>(json, _jsonOptions);

            if (session == null)
            {
                throw new InvalidDataException("Failed to deserialize session.");
            }

            return session;
        }

        public bool Delete(string sessionId)
        {
            var path = GetSessionPath(sessionId);
            if (!File.Exists(path))
            {
                return false;
            }

            File.Delete(path);
            return true;
        }

        private string GetSessionPath(string sessionId) => Path.Combine(_rootDirectory, sessionId + ".json");
    }

    public sealed class UserSession
    {
        public string SessionId { get; set; } = string.Empty;
        public string UserId { get; set; } = string.Empty;
        public DateTime LastUpdatedUtc { get; set; }
        public UserPreferences Preferences { get; set; } = new UserPreferences();
        public List<CartItem> ShoppingCart { get; set; } = new List<CartItem>();
        public List<Permission> Permissions { get; set; } = new List<Permission>();
    }

    public sealed class UserPreferences
    {
        public string Theme { get; set; } = "light";
        public string Language { get; set; } = "en-US";
        public bool ReceivePromotions { get; set; }
    }

    public sealed class CartItem
    {
        public string ProductId { get; set; } = string.Empty;
        public string Name { get; set; } = string.Empty;
        public int Quantity { get; set; }
        public decimal UnitPrice { get; set; }
    }

    public sealed class PermissionContext
    {
        public string UserRole { get; set; } = string.Empty;
        public string Region { get; set; } = string.Empty;
        public decimal CartTotal { get; set; }
    }

    [JsonPolymorphic(TypeDiscriminatorPropertyName = "$type")]
    [JsonDerivedType(typeof(RolePermission), "role")]
    [JsonDerivedType(typeof(MaxPurchasePermission), "max-purchase")]
    [JsonDerivedType(typeof(RegionPermission), "region")]
    public abstract class Permission
    {
        protected Permission()
        {
        }

        protected Permission(string name)
        {
            Name = name;
        }

        public string Name { get; set; } = string.Empty;

        public abstract bool IsAllowed(PermissionContext context);
    }

    public sealed class RolePermission : Permission
    {
        public RolePermission()
        {
        }

        public RolePermission(string name, params string[] allowedRoles) : base(name)
        {
            AllowedRoles = allowedRoles?.ToList() ?? new List<string>();
        }

        public List<string> AllowedRoles { get; set; } = new List<string>();

        public override bool IsAllowed(PermissionContext context)
        {
            if (context == null) throw new ArgumentNullException(nameof(context));
            return AllowedRoles.Any(role => string.Equals(role, context.UserRole, StringComparison.OrdinalIgnoreCase));
        }
    }

    public sealed class MaxPurchasePermission : Permission
    {
        public MaxPurchasePermission()
        {
        }

        public MaxPurchasePermission(string name, decimal maxAllowedTotal) : base(name)
        {
            MaxAllowedTotal = maxAllowedTotal;
        }

        public decimal MaxAllowedTotal { get; set; }

        public override bool IsAllowed(PermissionContext context)
        {
            if (context == null) throw new ArgumentNullException(nameof(context));
            return context.CartTotal <= MaxAllowedTotal;
        }
    }

    public sealed class RegionPermission : Permission
    {
        public RegionPermission()
        {
        }

        public RegionPermission(string name, params string[] allowedRegions) : base(name)
        {
            AllowedRegions = allowedRegions?.ToList() ?? new List<string>();
        }

        public List<string> AllowedRegions { get; set; } = new List<string>();

        public override bool IsAllowed(PermissionContext context)
        {
            if (context == null) throw new ArgumentNullException(nameof(context));
            return AllowedRegions.Any(region => string.Equals(region, context.Region, StringComparison.OrdinalIgnoreCase));
        }
    }
}