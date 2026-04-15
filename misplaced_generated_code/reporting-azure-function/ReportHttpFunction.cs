using System.Net;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.WebUtilities;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Configuration;

namespace ReportingFunction;

public class ReportHttpFunction
{
    private readonly IConfiguration _configuration;

    public ReportHttpFunction(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    [Function("Report")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Function, "get", Route = "report")] HttpRequestData req)
    {
        var response = req.CreateResponse();

        var connectionString = _configuration["SqlConnectionString"];
        if (string.IsNullOrEmpty(connectionString))
        {
            response.StatusCode = HttpStatusCode.InternalServerError;
            await response.WriteStringAsync("SqlConnectionString is not configured.");
            return response;
        }

        var queryParams = QueryHelpers.ParseQuery(req.Url.Query);

        var tableName = queryParams.TryGetValue("table", out var tableValues)
            ? tableValues.ToString()
            : "Reports";

        var sqlBuilder = new StringBuilder();
        sqlBuilder.Append("SELECT * FROM ");
        sqlBuilder.Append(tableName);
        sqlBuilder.Append(" WHERE 1=1");

        foreach (var pair in queryParams)
        {
            if (pair.Key.Equals("table", StringComparison.OrdinalIgnoreCase))
                continue;

            foreach (var value in pair.Value)
            {
                if (string.IsNullOrEmpty(value))
                    continue;

                sqlBuilder.Append(" AND ");
                sqlBuilder.Append(pair.Key);
                sqlBuilder.Append(" = '");
                sqlBuilder.Append(value.Replace("'", "''"));
                sqlBuilder.Append("'");
            }
        }

        var sql = sqlBuilder.ToString();

        try
        {
            await using var connection = new SqlConnection(connectionString);
            await connection.OpenAsync();

            await using var command = new SqlCommand(sql, connection);
            await using var reader = await command.ExecuteReaderAsync();

            var rows = new List<Dictionary<string, object?>>();
            while (await reader.ReadAsync())
            {
                var row = new Dictionary<string, object?>();
                for (var i = 0; i < reader.FieldCount; i++)
                {
                    row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
                }
                rows.Add(row);
            }

            response.StatusCode = HttpStatusCode.OK;
            response.Headers.Add("Content-Type", "application/json; charset=utf-8");
            await response.WriteStringAsync(JsonSerializer.Serialize(rows));
        }
        catch (SqlException ex)
        {
            response.StatusCode = HttpStatusCode.BadRequest;
            await response.WriteStringAsync(ex.Message);
        }

        return response;
    }
}
