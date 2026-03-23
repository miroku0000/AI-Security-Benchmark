using InvoiceApi.Models;

namespace InvoiceApi.Services;

public interface IInvoiceService
{
    Task<InvoiceDetails?> GetInvoiceDetailsAsync(string userId, string invoiceId, CancellationToken cancellationToken = default);
}
