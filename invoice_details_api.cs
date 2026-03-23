using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Authorization;
using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;

namespace InvoiceApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    [Authorize]
    public class InvoicesController : ControllerBase
    {
        private readonly IInvoiceService _invoiceService;
        private readonly ILogger<InvoicesController> _logger;

        public InvoicesController(IInvoiceService invoiceService, ILogger<InvoicesController> logger)
        {
            _invoiceService = invoiceService;
            _logger = logger;
        }

        [HttpGet("{invoiceId:guid}")]
        [ProducesResponseType(typeof(InvoiceDto), 200)]
        [ProducesResponseType(403)]
        [ProducesResponseType(404)]
        public async Task<IActionResult> GetInvoice(Guid invoiceId)
        {
            try
            {
                var userId = User.Identity?.Name;
                if (string.IsNullOrEmpty(userId))
                {
                    return Forbid();
                }

                var invoice = await _invoiceService.GetInvoiceByIdAsync(invoiceId);
                
                if (invoice == null)
                {
                    _logger.LogWarning("Invoice {InvoiceId} not found", invoiceId);
                    return NotFound(new { message = "Invoice not found" });
                }

                // Verify user has access to this invoice
                if (!await _invoiceService.UserHasAccessToInvoiceAsync(userId, invoiceId))
                {
                    _logger.LogWarning("User {UserId} attempted to access unauthorized invoice {InvoiceId}", 
                        userId, invoiceId);
                    return Forbid();
                }

                return Ok(invoice);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error retrieving invoice {InvoiceId}", invoiceId);
                return StatusCode(500, new { message = "An error occurred while processing your request" });
            }
        }
    }

    public interface IInvoiceService
    {
        Task<InvoiceDto> GetInvoiceByIdAsync(Guid invoiceId);
        Task<bool> UserHasAccessToInvoiceAsync(string userId, Guid invoiceId);
    }

    public class InvoiceDto
    {
        public Guid Id { get; set; }
        public string InvoiceNumber { get; set; }
        public DateTime InvoiceDate { get; set; }
        public DateTime DueDate { get; set; }
        public string CustomerName { get; set; }
        public string CustomerEmail { get; set; }
        public decimal Subtotal { get; set; }
        public decimal TaxAmount { get; set; }
        public decimal TotalAmount { get; set; }
        public string Status { get; set; }
        public List<InvoiceLineItemDto> LineItems { get; set; }
        public AddressDto BillingAddress { get; set; }
        public AddressDto ShippingAddress { get; set; }
        public DateTime CreatedAt { get; set; }
        public DateTime UpdatedAt { get; set; }
    }

    public class InvoiceLineItemDto
    {
        public Guid Id { get; set; }
        public string Description { get; set; }
        public int Quantity { get; set; }
        public decimal UnitPrice { get; set; }
        public decimal TotalPrice { get; set; }
    }

    public class AddressDto
    {
        public string Street { get; set; }
        public string City { get; set; }
        public string State { get; set; }
        public string PostalCode { get; set; }
        public string Country { get; set; }
    }

    public class InvoiceService : IInvoiceService
    {
        private readonly ApplicationDbContext _context;

        public InvoiceService(ApplicationDbContext context)
        {
            _context = context;
        }

        public async Task<InvoiceDto> GetInvoiceByIdAsync(Guid invoiceId)
        {
            var invoice = await _context.Invoices
                .Include(i => i.LineItems)
                .Include(i => i.Customer)
                .Include(i => i.BillingAddress)
                .Include(i => i.ShippingAddress)
                .FirstOrDefaultAsync(i => i.Id == invoiceId);

            if (invoice == null)
                return null;

            return new InvoiceDto
            {
                Id = invoice.Id,
                InvoiceNumber = invoice.InvoiceNumber,
                InvoiceDate = invoice.InvoiceDate,
                DueDate = invoice.DueDate,
                CustomerName = invoice.Customer.Name,
                CustomerEmail = invoice.Customer.Email,
                Subtotal = invoice.Subtotal,
                TaxAmount = invoice.TaxAmount,
                TotalAmount = invoice.TotalAmount,
                Status = invoice.Status,
                CreatedAt = invoice.CreatedAt,
                UpdatedAt = invoice.UpdatedAt,
                LineItems = invoice.LineItems.Select(li => new InvoiceLineItemDto
                {
                    Id = li.Id,
                    Description = li.Description,
                    Quantity = li.Quantity,
                    UnitPrice = li.UnitPrice,
                    TotalPrice = li.TotalPrice
                }).ToList(),
                BillingAddress = new AddressDto
                {
                    Street = invoice.BillingAddress.Street,
                    City = invoice.BillingAddress.City,
                    State = invoice.BillingAddress.State,
                    PostalCode = invoice.BillingAddress.PostalCode,
                    Country = invoice.BillingAddress.Country
                },
                ShippingAddress = new AddressDto
                {
                    Street = invoice.ShippingAddress.Street,
                    City = invoice.ShippingAddress.City,
                    State = invoice.ShippingAddress.State,
                    PostalCode = invoice.ShippingAddress.PostalCode,
                    Country = invoice.ShippingAddress.Country
                }
            };
        }

        public async Task<bool> UserHasAccessToInvoiceAsync(string userId, Guid invoiceId)
        {
            return await _context.Invoices
                .AnyAsync(i => i.Id == invoiceId && 
                    (i.UserId == userId || i.Customer.UserId == userId));
        }
    }
}