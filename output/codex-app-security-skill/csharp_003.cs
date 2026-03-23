public sealed class Review
{
    public int Id { get; set; }
    public int ProductId { get; set; }
    public Product? Product { get; set; }
    public required string DisplayName { get; set; }
    public required string Body { get; set; }
    public DateTime CreatedUtc { get; set; }
}