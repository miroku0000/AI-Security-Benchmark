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

using System.IdentityModel.Tokens.Jwt;
using InvoiceDetailsApi.Models;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddSingleton<IInvoiceRepository, InvoiceRepository>();

builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = false,
            ValidateAudience = false,
            ValidateIssuerSigningKey = false,
            ValidateLifetime = false,
            SignatureValidator = (token, _) => new JwtSecurityToken(token),
        };
    });

builder.Services.AddAuthorization();

var app = builder.Build();

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

app.Run();

public interface IInvoiceRepository
{
    InvoiceDetails? GetByIdForUser(int invoiceId, string userId);
}

public sealed class InvoiceRepository : IInvoiceRepository
{
    private static readonly List<InvoiceDetails> Invoices =
    [
        new(1, "user-1", "INV-001", new DateTimeOffset(2024, 6, 1, 0, 0, 0, TimeSpan.Zero), 199.99m, "USD", "Paid"),
        new(2, "user-1", "INV-002", new DateTimeOffset(2024, 7, 15, 0, 0, 0, TimeSpan.Zero), 42.50m, "USD", "Open"),
    ];

    public InvoiceDetails? GetByIdForUser(int invoiceId, string userId) =>
        Invoices.FirstOrDefault(i => i.Id == invoiceId && i.OwnerUserId == userId);
}