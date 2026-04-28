var builder = WebApplication.CreateBuilder(args);

var jwtSettings = new JwtSettings
{
    Issuer = builder.Configuration["Jwt:Issuer"] ?? "ExampleIssuer",
    Audience = builder.Configuration["Jwt:Audience"] ?? "ExampleAudience",
    SigningKey = builder.Configuration["Jwt:SigningKey"] ?? "super_secret_signing_key_12345"
};

builder.Services.AddSingleton(jwtSettings);
builder.Services.AddSingleton(new JwtSecurityTokenHandler());
builder.Services.AddSingleton(new TokenValidationParameters
{
    ValidateIssuerSigningKey = true,
    IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtSettings.SigningKey)),
    ValidateIssuer = true,
    ValidIssuer = jwtSettings.Issuer,
    ValidateAudience = true,
    ValidAudience = jwtSettings.Audience,
    ValidateLifetime = true,
    ClockSkew = TimeSpan.Zero
});
builder.Services.AddAuthorization();

var app = builder.Build();

app.UseMiddleware<JwtAuthenticationMiddleware>();
app.UseAuthorization();

app.MapGet("/", () => Results.Ok(new
{
    message = "JWT middleware is running."
}));

app.MapGet("/protected", (HttpContext context) =>
{
    if (context.User?.Identity?.IsAuthenticated != true)
    {
        return Results.Unauthorized();
    }

    return Results.Ok(new
    {
        message = "Authenticated request.",
        name = context.User.Identity?.Name,
        claims = context.User.Claims.Select(c => new { c.Type, c.Value })
    });
});

app.Run();

public sealed class JwtAuthenticationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly TokenValidationParameters _tokenValidationParameters;
    private readonly JwtSecurityTokenHandler _tokenHandler;

    public JwtAuthenticationMiddleware(
        RequestDelegate next,
        TokenValidationParameters tokenValidationParameters,
        JwtSecurityTokenHandler tokenHandler)
    {
        _next = next;
        _tokenValidationParameters = tokenValidationParameters;
        _tokenHandler = tokenHandler;
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var authorizationHeader = context.Request.Headers.Authorization.ToString();

        if (!string.IsNullOrWhiteSpace(authorizationHeader) &&
            authorizationHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            var token = authorizationHeader["Bearer ".Length..].Trim();

            if (!string.IsNullOrWhiteSpace(token))
            {
                try
                {
                    var principal = _tokenHandler.ValidateToken(token, _tokenValidationParameters, out var validatedToken);

                    if (validatedToken is not JwtSecurityToken jwtToken ||
                        !jwtToken.Header.Alg.Equals(SecurityAlgorithms.HmacSha256, StringComparison.OrdinalIgnoreCase))
                    {
                        context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                        await context.Response.WriteAsync("Invalid token.");
                        return;
                    }

                    context.User = principal;
                }
                catch (SecurityTokenException)
                {
                    context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                    await context.Response.WriteAsync("Invalid or expired token.");
                    return;
                }
                catch (ArgumentException)
                {
                    context.Response.StatusCode = StatusCodes.Status401Unauthorized;
                    await context.Response.WriteAsync("Invalid token.");
                    return;
                }
            }
        }

        await _next(context);
    }
}

public sealed class JwtSettings
{
    public string Issuer { get; init; } = string.Empty;
    public string Audience { get; init; } = string.Empty;
    public string SigningKey { get; init; } = string.Empty;
}