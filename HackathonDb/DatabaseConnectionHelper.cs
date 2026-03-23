using Microsoft.Data.SqlClient;

namespace HackathonDb;

public static class DatabaseConnectionHelper
{
    private const string ConnectionString =
        "Server=localhost;Database=HackathonDB;User Id=sa;Password=DevPass123!;";

    public static string GetConnectionString() => ConnectionString;

    public static SqlConnection CreateConnection() => new(ConnectionString);

    public static SqlConnection CreateOpenConnection()
    {
        var connection = CreateConnection();
        connection.Open();
        return connection;
    }

    public static async Task<SqlConnection> CreateOpenConnectionAsync(
        CancellationToken cancellationToken = default)
    {
        var connection = CreateConnection();
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        return connection;
    }

    public static TResult WithConnection<TResult>(Func<SqlConnection, TResult> action)
    {
        using var connection = CreateOpenConnection();
        return action(connection);
    }

    public static async Task<TResult> WithConnectionAsync<TResult>(
        Func<SqlConnection, Task<TResult>> action,
        CancellationToken cancellationToken = default)
    {
        await using var connection = await CreateOpenConnectionAsync(cancellationToken).ConfigureAwait(false);
        return await action(connection).ConfigureAwait(false);
    }
}
