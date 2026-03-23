using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<JwtAuthenticationOptions>(builder.Configuration.GetSection("Jwt"));
builder.Services.AddSingleton<JwtAuthenticationMiddleware>();

var app = builder.Build();

app.UseMiddleware<JwtAuthenticationMiddleware>();

app.MapGet("/", () => "ok");
app.MapGet("/whoami", (HttpContext ctx) =>
    ctx.User.Identity?.IsAuthenticated == true
        ? Results.Ok(new { name = ctx.User.Identity?.Name, claims = ctx.User.Claims.Select(c => new { c.Type, c.Value }) })
        : Results.Unauthorized());

app.Run();

public sealed class JwtAuthenticationOptions
{
    public string Issuer { get; set; } = string.Empty;
    public string Audience { get; set; } = string.Empty;
    public string SigningKey { get; set; } = string.Empty;
}

public sealed class JwtAuthenticationMiddleware : IMiddleware
{
    private readonly TokenValidationParameters _validationParameters;

    public JwtAuthenticationMiddleware(IOptions<JwtAuthenticationOptions> optionsAccessor)
    {
        var o = optionsAccessor.Value;
        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(o.SigningKey));

        _validationParameters = new TokenValidationParameters
        {
            ValidIssuer = o.Issuer,
            ValidAudience = o.Audience,
            IssuerSigningKey = key,
            ValidateIssuerSigningKey = true,
            ValidateIssuer = !string.IsNullOrEmpty(o.Issuer),
            ValidateAudience = !string.IsNullOrEmpty(o.Audience),
            ValidateLifetime = true,
            ClockSkew = TimeSpan.FromMinutes(1),
            NameClaimType = ClaimTypes.NameIdentifier,
            RoleClaimType = ClaimTypes.Role
        };
    }

    public async Task InvokeAsync(HttpContext context, RequestDelegate next)
    {
        if (!context.Request.Headers.TryGetValue("Authorization", out var authValues))
        {
            await next(context);
            return;
        }

        var auth = authValues.ToString();
        const string prefix = "Bearer ";
        if (string.IsNullOrWhiteSpace(auth) || !auth.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
        {
            await next(context);
            return;
        }

        var token = auth.AsSpan(prefix.Length).Trim().ToString();
        if (string.IsNullOrEmpty(token))
        {
            await next(context);
            return;
        }

        var handler = new JwtSecurityTokenHandler();
        try
        {
            var principal = handler.ValidateToken(token, _validationParameters, out _);
            context.User = principal;
        }
        catch (SecurityTokenException)
        {
            // Invalid token: leave User unauthenticated
        }

        await next(context);
    }
}
