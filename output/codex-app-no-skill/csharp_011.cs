public sealed class InMemoryInvoiceRepository : IInvoiceRepository
{
    private readonly Dictionary<Guid, InvoiceDetail> _invoices;