using System.Security.Claims;
using InvoiceDetailsApi.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace InvoiceDetailsApi.Controllers;

[ApiController]
[Authorize]
[Route("api/[controller]")]
public sealed class InvoicesController : ControllerBase
{
    private readonly IInvoiceRepository _invoices;

    public InvoicesController(IInvoiceRepository invoices)
    {
        _invoices = invoices;
    }

    [HttpGet("{invoiceId:int}")]
    [ProducesResponseType(typeof(InvoiceDetails), StatusCodes.Status200OK)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(StatusCodes.Status404NotFound)]
    public ActionResult<InvoiceDetails> GetById([FromRoute] int invoiceId)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier) ?? User.Identity?.Name;
        if (string.IsNullOrEmpty(userId))
        {
            return Unauthorized();
        }

        var invoice = _invoices.GetByIdForUser(invoiceId, userId);
        if (invoice is null)
        {
            return NotFound();
        }

        return Ok(invoice);
    }
}
