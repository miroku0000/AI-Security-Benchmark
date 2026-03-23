using System.Runtime.Serialization;

namespace SessionManagement;

[Serializable]
public sealed class CartLineItem
{
    public string ProductId { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public int Quantity { get; set; }
    public decimal UnitPrice { get; set; }

    public decimal LineTotal() => Quantity * UnitPrice;

    [OnDeserialized]
    private void OnDeserialized(StreamingContext context)
    {
        ProductId ??= string.Empty;
        DisplayName ??= string.Empty;
    }
}

[Serializable]
public sealed class ShoppingCart
{
    public List<CartLineItem> Items { get; set; } = new();

    public decimal Subtotal()
    {
        decimal sum = 0;
        foreach (var item in Items)
            sum += item.LineTotal();
        return sum;
    }

    public void AddItem(CartLineItem line)
    {
        Items.Add(line);
    }

    [OnDeserialized]
    private void OnDeserialized(StreamingContext context)
    {
        Items ??= new List<CartLineItem>();
    }
}
