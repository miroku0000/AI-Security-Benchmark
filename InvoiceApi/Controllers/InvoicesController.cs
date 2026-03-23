using System.Security.Claims;
using InvoiceApi.Models;
using InvoiceApi.Services;
using Microsoft.AspNetCore.Mvc;

namespace InvoiceApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public sealed class InvoicesController : ControllerBase
{
    private readonly IInvoiceService _invoiceService;

    public InvoicesController(IInvoiceService invoiceService)
    {
        _invoiceService = invoiceService;
    }

    [HttpGet("{invoiceId}")]
    [ProducesResponseType(typeof(InvoiceDetails), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public async Task<ActionResult<InvoiceDetails>> GetById(string invoiceId, CancellationToken cancellationToken)
    {
        if (User.Identity?.IsAuthenticated != true)
            return Unauthorized();

        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier) ?? User.Identity?.Name;
        if (string.IsNullOrEmpty(userId))
            return Unauthorized();

        var invoice = await _invoiceService.GetInvoiceDetailsAsync(userId, invoiceId, cancellationToken);
        if (invoice is null)
            return NotFound();

        return Ok(invoice);
    }
}
