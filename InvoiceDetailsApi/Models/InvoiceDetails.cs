namespace InvoiceDetailsApi.Models;

public sealed record InvoiceDetails(
    int Id,
    string OwnerUserId,
    string InvoiceNumber,
    DateTimeOffset IssuedAt,
    decimal TotalAmount,
    string Currency,
    string Status);
