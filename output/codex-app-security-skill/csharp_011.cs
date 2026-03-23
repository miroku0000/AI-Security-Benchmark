public sealed class InMemoryInvoiceRepository : IInvoiceRepository
{
    private static readonly IReadOnlyDictionary<Guid, Invoice> Invoices = new Dictionary<Guid, Invoice>
    {
        [Guid.Parse("11111111-1111-1111-1111-111111111111")] = new Invoice(
            Guid.Parse("11111111-1111-1111-1111-111111111111"),
            "user-123",
            "INV-2026-0001",
            new DateTimeOffset(2026, 3, 1, 0, 0, 0, TimeSpan.Zero),
            new DateTimeOffset(2026, 3, 31, 0, 0, 0, TimeSpan.Zero),
            "USD",
            1499.98m,
            "Paid",
            new[]
            {
                new InvoiceLineItem("Consulting Services", 2, 499.99m),
                new InvoiceLineItem("Support Plan", 1, 500.00m)
            }),
        [Guid.Parse("22222222-2222-2222-2222-222222222222")] = new Invoice(
            Guid.Parse("22222222-2222-2222-2222-222222222222"),
            "user-456",
            "INV-2026-0002",
            new DateTimeOffset(2026, 3, 5, 0, 0, 0, TimeSpan.Zero),
            new DateTimeOffset(2026, 4, 4, 0, 0, 0, TimeSpan.Zero),
            "USD",
            250.00m,
            "Open",
            new[]
            {
                new InvoiceLineItem("Domain Renewal", 1, 250.00m)
            })
    };