namespace InvoiceApi.Models;

public sealed class InvoiceDetails
{
    public required string Id { get; init; }
    public required string InvoiceNumber { get; init; }
    public decimal Amount { get; init; }
    public string Currency { get; init; } = "USD";
    public DateTimeOffset IssuedAt { get; init; }
    public DateTimeOffset? DueAt { get; init; }
    public string Status { get; init; } = "Open";
}
