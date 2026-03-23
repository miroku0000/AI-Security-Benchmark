namespace ProductReviewsMvc.ViewModels;

public class ProductReviewsViewModel
{
    public int ProductId { get; set; }
    public string ProductName { get; set; } = string.Empty;
    public IReadOnlyList<ProductReviewDisplayItem> Reviews { get; set; } = Array.Empty<ProductReviewDisplayItem>();
}

public class ProductReviewDisplayItem
{
    public string AuthorName { get; set; } = string.Empty;
    public string BodyHtmlSanitized { get; set; } = string.Empty;
    public int Rating { get; set; }
    public DateTime CreatedUtc { get; set; }
}
