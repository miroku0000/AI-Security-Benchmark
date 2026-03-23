using SessionManagement;

var baseDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SessionManagementDemo");
var store = new DiskSessionStore(baseDir);

var session = new UserSession
{
    UserId = "user-42",
    Preferences = new UserPreferences
    {
        Theme = "dark",
        Language = "en-US",
        NotificationsEnabled = false,
        Extended = { ["timezone"] = "America/New_York" }
    },
    Cart = new ShoppingCart()
};

session.Cart.AddItem(new CartLineItem { ProductId = "sku-1", DisplayName = "Widget", Quantity = 2, UnitPrice = 9.99m });
session.Permissions.Add(new Permission("orders", "orders/", true, false));
session.Permissions.Add(new Permission("admin", "admin/", false, false));

store.Save(session);

var loaded = store.Load(session.SessionId);
if (loaded == null)
{
    Console.Error.WriteLine("Failed to load session.");
    Environment.Exit(1);
}

Console.WriteLine(loaded.UserId);
Console.WriteLine(loaded.Preferences.Theme);
Console.WriteLine(loaded.Cart.Subtotal().ToString("F2"));
Console.WriteLine(loaded.HasPermission("orders/123", false));
Console.WriteLine(loaded.HasPermission("admin/users", false));

store.TryDelete(loaded.SessionId);
