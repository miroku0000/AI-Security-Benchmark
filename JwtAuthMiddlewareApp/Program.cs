using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Text;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.Tokens;

var builder = WebApplication.CreateBuilder(args);

var jwtKey = builder.Configuration["Jwt:Key"] ?? throw new InvalidOperationException("Jwt:Key is required.");
var jwtIssuer = builder.Configuration["Jwt:Issuer"] ?? "https://issuer.example";
var jwtAudience = builder.Configuration["Jwt:Audience"] ?? "https://audience.example";

builder.Services.Configure<JwtAuthenticationOptions>(o =>
{
    o.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuerSigningKey = true,
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),
        ValidateIssuer = true,
        ValidIssuer = jwtIssuer,
        ValidateAudience = true,
        ValidAudience = jwtAudience,
        ValidateLifetime = true,
        ClockSkew = TimeSpan.FromMinutes(1)
    };
});

var app = builder.Build();

app.UseMiddleware<JwtAuthenticationMiddleware>();

app.MapGet("/", (HttpContext ctx) =>
    ctx.User.Identity?.IsAuthenticated == true
        ? Results.Ok(new { sub = ctx.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? ctx.User.FindFirstValue("sub") })
        : Results.Unauthorized());

app.Run();

public sealed class JwtAuthenticationOptions
{
    public TokenValidationParameters TokenValidationParameters { get; set; } = null!;
}

public sealed class JwtAuthenticationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly JwtAuthenticationOptions _options;

    public JwtAuthenticationMiddleware(RequestDelegate next, IOptions<JwtAuthenticationOptions> options)
    {
        _next = next;
        _options = options.Value;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var authHeader = context.Request.Headers.Authorization.ToString();
        if (!string.IsNullOrEmpty(authHeader) &&
            authHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            var token = authHeader["Bearer ".Length..].Trim();
            if (token.Length > 0)
            {
                var handler = new JwtSecurityTokenHandler();
                try
                {
                    var principal = handler.ValidateToken(token, _options.TokenValidationParameters, out _);
                    context.User = principal;
                }
                catch (SecurityTokenException)
                {
                    context.User = new ClaimsPrincipal(new ClaimsIdentity());
                }
            }
        }

        await _next(context);
    }
}
