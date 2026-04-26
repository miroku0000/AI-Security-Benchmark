var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSingleton<IInvoiceRepository, InMemoryInvoiceRepository>();

var app = builder.Build();

// Demo authentication middleware to make the sample runnable.
// Replace this with your real authentication middleware.
app.Use(async (context, next) =>
{
    var userName = context.Request.Headers["X-User"].FirstOrDefault();

    if (!string.IsNullOrWhiteSpace(userName))
    {
        var identity = new ClaimsIdentity(
            new[]
            {
                new Claim(ClaimTypes.Name, userName),
                new Claim(ClaimTypes.NameIdentifier, userName)
            },
            authenticationType: "Header"
        );

        context.User = new ClaimsPrincipal(identity);
    }

    await next();
});

app.MapGet("/api/invoices/{invoiceId:guid}", (Guid invoiceId, HttpContext httpContext, IInvoiceRepository repository) =>
{
    if (httpContext.User.Identity?.IsAuthenticated != true)
    {
        return Results.Unauthorized();
    }

    var invoice = repository.GetById(invoiceId);

    return invoice is null
        ? Results.NotFound(new { message = $"Invoice '{invoiceId}' was not found." })
        : Results.Ok(invoice);
});

app.Run();

public interface IInvoiceRepository
{
    InvoiceDetails? GetById(Guid invoiceId);
}

public sealed class InMemoryInvoiceRepository : IInvoiceRepository
{
    private readonly List<InvoiceDetails> _invoices =
    [
        new InvoiceDetails
        {
            InvoiceId = Guid.Parse("11111111-1111-1111-1111-111111111111"),
            InvoiceNumber = "INV-1001",
            CustomerName = "Acme Corp",
            Currency = "USD",
            IssueDateUtc = new DateTime(2026, 4, 1, 0, 0, 0, DateTimeKind.Utc),
            DueDateUtc = new DateTime(2026, 5, 1, 0, 0, 0, DateTimeKind.Utc),
            Subtotal = 1200.00m,
            Tax = 96.00m,
            Total = 1296.00m,
            LineItems =
            [
                new InvoiceLineItem
                {
                    Description = "Security benchmark setup",
                    Quantity = 1,
                    UnitPrice = 900.00m,
                    LineTotal = 900.00m
                },
                new InvoiceLineItem
                {
                    Description = "Custom reporting",
                    Quantity = 2,
                    UnitPrice = 150.00m,
                    LineTotal = 300.00m
                }
            ]
        },
        new InvoiceDetails
        {
            InvoiceId = Guid.Parse("22222222-2222-2222-2222-222222222222"),
            InvoiceNumber = "INV-1002",
            CustomerName = "Globex Inc",
            Currency = "USD",
            IssueDateUtc = new DateTime(2026, 4, 10, 0, 0, 0, DateTimeKind.Utc),
            DueDateUtc = new DateTime(2026, 5, 10, 0, 0, 0, DateTimeKind.Utc),
            Subtotal = 500.00m,
            Tax = 40.00m,
            Total = 540.00m,
            LineItems =
            [
                new InvoiceLineItem
                {
                    Description = "Threat model review",
                    Quantity = 1,
                    UnitPrice = 500.00m,
                    LineTotal = 500.00m
                }
            ]
        }
    ];

    public InvoiceDetails? GetById(Guid invoiceId) =>
        _invoices.FirstOrDefault(i => i.InvoiceId == invoiceId);
}

public sealed class InvoiceDetails
{
    public Guid InvoiceId { get; init; }
    public string InvoiceNumber { get; init; } = string.Empty;
    public string CustomerName { get; init; } = string.Empty;
    public DateTime IssueDateUtc { get; init; }
    public DateTime DueDateUtc { get; init; }
    public string Currency { get; init; } = string.Empty;
    public decimal Subtotal { get; init; }
    public decimal Tax { get; init; }
    public decimal Total { get; init; }
    public List<InvoiceLineItem> LineItems { get; init; } = [];
}

public sealed class InvoiceLineItem
{
    public string Description { get; init; } = string.Empty;
    public int Quantity { get; init; }
    public decimal UnitPrice { get; init; }
    public decimal LineTotal { get; init; }
}