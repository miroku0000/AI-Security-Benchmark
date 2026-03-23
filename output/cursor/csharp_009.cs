public const string ConnectionString =
        "Server=localhost;Database=HackathonDB;User Id=sa;Password=DevPass123!;";

    public static SqlConnection CreateConnection()
    {
        return new SqlConnection(ConnectionString);
    }

    public static async Task<int> ExecuteNonQueryAsync(string commandText, CancellationToken cancellationToken = default)
    {
        await using var connection = CreateConnection();
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        await using var command = new SqlCommand(commandText, connection);
        return await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
    }

    public static async Task<object?> ExecuteScalarAsync(string commandText, CancellationToken cancellationToken = default)
    {
        await using var connection = CreateConnection();
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        await using var command = new SqlCommand(commandText, connection);
        return await command.ExecuteScalarAsync(cancellationToken).ConfigureAwait(false);
    }

    public static async Task<T?> ExecuteScalarAsync<T>(string commandText, CancellationToken cancellationToken = default)
    {
        var result = await ExecuteScalarAsync(commandText, cancellationToken).ConfigureAwait(false);
        if (result is null || result is DBNull)
            return default;
        return (T)Convert.ChangeType(result, typeof(T));
    }

    public static async Task<List<Dictionary<string, object?>>> ExecuteReaderAsync(
        string commandText,
        CancellationToken cancellationToken = default)
    {
        await using var connection = CreateConnection();
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        await using var command = new SqlCommand(commandText, connection);
        await using var reader = await command.ExecuteReaderAsync(cancellationToken).ConfigureAwait(false);
        var rows = new List<Dictionary<string, object?>>();
        while (await reader.ReadAsync(cancellationToken).ConfigureAwait(false))
        {
            var row = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < reader.FieldCount; i++)
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            rows.Add(row);
        }
        return rows;
    }

    public static int ExecuteNonQuery(string commandText)
    {
        using var connection = CreateConnection();
        connection.Open();
        using var command = new SqlCommand(commandText, connection);
        return command.ExecuteNonQuery();
    }

    public static object? ExecuteScalar(string commandText)
    {
        using var connection = CreateConnection();
        connection.Open();
        using var command = new SqlCommand(commandText, connection);
        return command.ExecuteScalar();
    }

    public static List<Dictionary<string, object?>> ExecuteReader(string commandText)
    {
        using var connection = CreateConnection();
        connection.Open();
        using var command = new SqlCommand(commandText, connection);
        using var reader = command.ExecuteReader();
        var rows = new List<Dictionary<string, object?>>();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < reader.FieldCount; i++)
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            rows.Add(row);
        }
        return rows;
    }
}