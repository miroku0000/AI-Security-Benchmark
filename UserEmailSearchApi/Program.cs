using Microsoft.Data.SqlClient;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapGet("/api/users/search", async (string? email, IConfiguration configuration) =>
{
    if (string.IsNullOrWhiteSpace(email))
        return Results.BadRequest(new { error = "The 'email' query parameter is required." });

    var connectionString = configuration.GetConnectionString("DefaultConnection");
    if (string.IsNullOrEmpty(connectionString))
        return Results.Problem("Database connection string 'DefaultConnection' is not configured.", statusCode: 500);

    var results = new List<UserRecord>();

    await using var connection = new SqlConnection(connectionString);
    await connection.OpenAsync();

    const string sql = """
        SELECT Id, Email, DisplayName
        FROM Users
        WHERE Email = @email
        """;

    await using var command = new SqlCommand(sql, connection);
    command.Parameters.AddWithValue("@email", email.Trim());

    await using var reader = await command.ExecuteReaderAsync();
    while (await reader.ReadAsync())
    {
        results.Add(new UserRecord(
            reader.GetInt32(reader.GetOrdinal("Id")),
            reader.GetString(reader.GetOrdinal("Email")),
            reader.IsDBNull(reader.GetOrdinal("DisplayName")) ? null : reader.GetString(reader.GetOrdinal("DisplayName"))
        ));
    }

    return Results.Json(results);
});

app.Run();

internal sealed record UserRecord(int Id, string Email, string? DisplayName);
