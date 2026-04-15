using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Logging;

namespace DebugLoggingFunction;

public static class SqlLogging
{
    public static async Task<int> ExecuteNonQueryWithLoggingAsync(
        string connectionString,
        string commandText,
        IReadOnlyList<SqlParameter> parameters,
        ILogger logger,
        CancellationToken cancellationToken)
    {
        logger.LogInformation("SQL command text: {CommandText}", commandText);
        for (var i = 0; i < parameters.Count; i++)
        {
            var p = parameters[i];
            logger.LogInformation(
                "SQL parameter {Index} name={Name} type={Type} value={Value}",
                i,
                p.ParameterName,
                p.SqlDbType,
                p.Value is DBNull ? "NULL" : p.Value);
        }

        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync(cancellationToken).ConfigureAwait(false);
        await using var command = new SqlCommand(commandText, connection);
        foreach (var p in parameters)
        {
            var copy = new SqlParameter(p.ParameterName, p.Value ?? DBNull.Value)
            {
                SqlDbType = p.SqlDbType,
                Direction = p.Direction,
                Size = p.Size,
                IsNullable = p.IsNullable,
                Precision = p.Precision,
                Scale = p.Scale
            };
            command.Parameters.Add(copy);
        }

        try
        {
            var rows = await command.ExecuteNonQueryAsync(cancellationToken).ConfigureAwait(false);
            logger.LogInformation("SQL execute completed rowsAffected={Rows}", rows);
            return rows;
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "SQL execute failed. Command={CommandText}", commandText);
            throw;
        }
    }
}
