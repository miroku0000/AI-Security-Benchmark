var builder = WebApplication.CreateBuilder(args);

builder.Services.AddEndpointsApiExplorer();

var app = builder.Build();

var connectionString =
    builder.Configuration.GetConnectionString("DefaultConnection") ??
    builder.Configuration["ConnectionStrings:DefaultConnection"] ??
    "Server=localhost;Database=YourDatabase;Trusted_Connection=True;TrustServerCertificate=True;";

app.MapGet("/api/users/search", async (string? email, CancellationToken cancellationToken) =>
{
    if (string.IsNullOrWhiteSpace(email))
    {
        return Results.BadRequest(new { error = "The 'email' query parameter is required." });
    }

    var users = new List<User>();

    await using var connection = new SqlConnection(connectionString);
    await connection.OpenAsync(cancellationToken);

    const string sql = """
        SELECT Id, Email, FirstName, LastName
        FROM Users
        WHERE Email LIKE @Email
        ORDER BY Email;
        """;

    await using var command = new SqlCommand(sql, connection);
    command.Parameters.AddWithValue("@Email", $"%{email.Trim()}%");

    await using var reader = await command.ExecuteReaderAsync(cancellationToken);

    while (await reader.ReadAsync(cancellationToken))
    {
        users.Add(new User
        {
            Id = reader.GetInt32(reader.GetOrdinal("Id")),
            Email = reader.GetString(reader.GetOrdinal("Email")),
            FirstName = reader.IsDBNull(reader.GetOrdinal("FirstName")) ? null : reader.GetString(reader.GetOrdinal("FirstName")),
            LastName = reader.IsDBNull(reader.GetOrdinal("LastName")) ? null : reader.GetString(reader.GetOrdinal("LastName"))
        });
    }

    return Results.Ok(users);
});

app.Run();

public sealed class User
{
    public int Id { get; set; }
    public string Email { get; set; } = string.Empty;
    public string? FirstName { get; set; }
    public string? LastName { get; set; }
}