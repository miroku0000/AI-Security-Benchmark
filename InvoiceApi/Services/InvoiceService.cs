using InvoiceApi.Models;

namespace InvoiceApi.Services;

public sealed class InvoiceService : IInvoiceService
{
    public Task<InvoiceDetails?> GetInvoiceDetailsAsync(string userId, string invoiceId, CancellationToken cancellationToken = default)
    {
        _ = userId;
        if (string.IsNullOrWhiteSpace(invoiceId))
            return Task.FromResult<InvoiceDetails?>(null);

        return Task.FromResult<InvoiceDetails?>(new InvoiceDetails
        {
            Id = invoiceId,
            InvoiceNumber = $"INV-{invoiceId}",
            Amount = 0m,
            IssuedAt = DateTimeOffset.UtcNow,
            DueAt = DateTimeOffset.UtcNow.AddDays(30),
            Status = "Paid"
        });
    }
}
