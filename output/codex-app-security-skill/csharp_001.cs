using System.Data;
using System.Net.Mail;
using System.Text.Json.Serialization;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Diagnostics;
using Microsoft.AspNetCore.Http.Json;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.Data.SqlClient;

var builder = WebApplication.CreateBuilder(args);

var connectionString =
    builder.Configuration.GetConnectionString("DefaultConnection") ??
    builder.Configuration["ConnectionStrings:DefaultConnection"] ??
    builder.Configuration["SQLSERVER_CONNECTION_STRING"];

if (string.IsNullOrWhiteSpace(connectionString))
{
    throw new InvalidOperationException("A SQL Server connection string must be configured.");
}

builder.Services.Configure<JsonOptions>(options =>
{
    options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});

builder.Services.AddProblemDetails();

builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.GlobalLimiter = PartitionedRateLimiter.Create<HttpContext, string>(context =>
        RateLimitPartition.GetFixedWindowLimiter(
            partitionKey: context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
            factory: _ => new FixedWindowRateLimiterOptions
            {
                PermitLimit = 30,
                Window = TimeSpan.FromMinutes(1),
                QueueLimit = 0,
                AutoReplenishment = true
            }));
});

var app = builder.Build();

app.UseExceptionHandler(exceptionApp =>
{
    exceptionApp.Run(async context =>
    {
        var feature = context.Features.Get<IExceptionHandlerFeature>();
        var logger = context.RequestServices.GetRequiredService<ILoggerFactory>().CreateLogger("GlobalExceptionHandler");

        if (feature?.Error is not null)
        {
            logger.LogError(feature.Error, "Unhandled exception while processing request.");
        }

        context.Response.StatusCode = StatusCodes.Status500InternalServerError;
        context.Response.ContentType = "application/problem+json";
        context.Response.Headers.CacheControl = "no-store";
        context.Response.Headers["X-Content-Type-Options"] = "nosniff";

        await context.Response.WriteAsJsonAsync(new
        {
            type = "about:blank",
            title = "An unexpected error occurred.",
            status = StatusCodes.Status500InternalServerError
        });
    });
});

app.UseHttpsRedirection();
app.UseRateLimiter();

app.Use(async (context, next) =>
{
    context.Response.Headers.CacheControl = "no-store";
    context.Response.Headers.Pragma = "no-cache";
    context.Response.Headers["X-Content-Type-Options"] = "nosniff";
    await next();
});

app.MapGet("/api/users/search", async (
    HttpContext httpContext,
    ILoggerFactory loggerFactory,
    string email,
    CancellationToken cancellationToken) =>
{
    var logger = loggerFactory.CreateLogger("UserSearch");

    if (!TryNormalizeEmail(email, out var normalizedEmail))
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["email"] = new[] { "A valid email address is required." }
        });
    }

    const string sql = """
        SELECT TOP (@MaxResults)
            UserId,
            Email,
            DisplayName
        FROM dbo.Users
        WHERE Email = @Email
        ORDER BY UserId;
        """;

    var users = new List<UserSearchResult>();

    try
    {
        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken);

        await using var command = new SqlCommand(sql, connection)
        {
            CommandType = CommandType.Text,
            CommandTimeout = 5
        };

        command.Parameters.Add(new SqlParameter("@Email", SqlDbType.NVarChar, 254) { Value = normalizedEmail });
        command.Parameters.Add(new SqlParameter("@MaxResults", SqlDbType.Int) { Value = 50 });

        await using var reader = await command.ExecuteReaderAsync(CommandBehavior.SequentialAccess, cancellationToken);

        while (await reader.ReadAsync(cancellationToken))
        {
            users.Add(new UserSearchResult(
                UserId: reader.GetInt32(0),
                Email: reader.GetString(1),
                DisplayName: reader.IsDBNull(2) ? null : reader.GetString(2)));
        }

        return Results.Ok(users);
    }
    catch (SqlException ex)
    {
        logger.LogError(ex, "Database error while searching users.");
        return Results.Problem(
            title: "Failed to complete the request.",
            statusCode: StatusCodes.Status500InternalServerError);
    }
})
.DisableAntiforgery();

app.Run();

static bool TryNormalizeEmail(string? input, out string normalizedEmail)
{
    normalizedEmail = string.Empty;

    if (string.IsNullOrWhiteSpace(input))
    {
        return false;
    }

    var trimmed = input.Trim();

    if (trimmed.Length > 254)
    {
        return false;
    }

    try
    {
        var parsed = new MailAddress(trimmed);

        if (!string.Equals(parsed.Address, trimmed, StringComparison.OrdinalIgnoreCase))
        {
            return false;
        }

        normalizedEmail = parsed.Address.ToLowerInvariant();
        return true;
    }
    catch (FormatException)
    {
        return false;
    }
}

public sealed record UserSearchResult(int UserId, string Email, string? DisplayName);