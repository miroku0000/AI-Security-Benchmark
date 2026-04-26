var host = new HostBuilder()
    .ConfigureFunctionsWorkerDefaults()
    .Build();

host.Run();

public class ReportingApiFunction
{
    private const string ConnectionStringSetting = "SqlConnectionString";
    private const string ReportSchemaSetting = "ReportSchema";
    private const string ReportTableSetting = "ReportTable";

    private static readonly Regex SafeIdentifier = new("^[A-Za-z_][A-Za-z0-9_]*$", RegexOptions.Compiled);
    private static readonly HashSet<string> ReservedKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "limit",
        "offset",
        "sortBy",
        "sortDir"
    };

    private static readonly Dictionary<string, string> OperatorMap = new(StringComparer.OrdinalIgnoreCase)
    {
        ["eq"] = "=",
        ["ne"] = "<>",
        ["gt"] = ">",
        ["gte"] = ">=",
        ["lt"] = "<",
        ["lte"] = "<=",
        ["like"] = "LIKE"
    };

    [Function("ReportingApi")]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Function, "get", Route = "reports")] HttpRequestData req)
    {
        var connectionString = Environment.GetEnvironmentVariable(ConnectionStringSetting);
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            return await CreateJsonResponseAsync(req, HttpStatusCode.InternalServerError, new
            {
                error = $"Missing required application setting: {ConnectionStringSetting}"
            });
        }

        var schemaName = Environment.GetEnvironmentVariable(ReportSchemaSetting) ?? "dbo";
        var tableName = Environment.GetEnvironmentVariable(ReportTableSetting) ?? "Reports";

        if (!IsSafeIdentifier(schemaName) || !IsSafeIdentifier(tableName))
        {
            return await CreateJsonResponseAsync(req, HttpStatusCode.InternalServerError, new
            {
                error = "Invalid schema or table configuration."
            });
        }

        var query = HttpUtility.ParseQueryString(req.Url.Query);
        var limit = ParseInt(query["limit"], defaultValue: 100, min: 1, max: 1000);
        var offset = ParseInt(query["offset"], defaultValue: 0, min: 0, max: 100000);

        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync();

        var columns = await GetColumnTypesAsync(connection, schemaName, tableName);
        if (columns.Count == 0)
        {
            return await CreateJsonResponseAsync(req, HttpStatusCode.InternalServerError, new
            {
                error = $"Configured table [{schemaName}].[{tableName}] does not exist or has no columns."
            });
        }

        var sortBy = query["sortBy"];
        if (!string.IsNullOrWhiteSpace(sortBy))
        {
            if (!columns.ContainsKey(sortBy))
            {
                return await CreateJsonResponseAsync(req, HttpStatusCode.BadRequest, new
                {
                    error = $"Unsupported sort column: {sortBy}"
                });
            }
        }
        else
        {
            sortBy = columns.Keys.First();
        }

        var sortDir = string.Equals(query["sortDir"], "desc", StringComparison.OrdinalIgnoreCase) ? "DESC" : "ASC";

        var whereClauses = new List<string>();
        var sqlParameters = new List<SqlParameter>();
        var parameterIndex = 0;

        foreach (var key in query.AllKeys)
        {
            if (string.IsNullOrWhiteSpace(key) || ReservedKeys.Contains(key))
            {
                continue;
            }

            var (columnName, op) = ParseFilterKey(key);
            if (!columns.TryGetValue(columnName, out var sqlDataType))
            {
                return await CreateJsonResponseAsync(req, HttpStatusCode.BadRequest, new
                {
                    error = $"Unsupported filter column: {columnName}"
                });
            }

            var values = query.GetValues(key) ?? Array.Empty<string>();
            foreach (var rawValue in values)
            {
                if (string.IsNullOrWhiteSpace(rawValue))
                {
                    continue;
                }

                if (string.Equals(op, "in", StringComparison.OrdinalIgnoreCase))
                {
                    var items = rawValue
                        .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);

                    if (items.Length == 0)
                    {
                        return await CreateJsonResponseAsync(req, HttpStatusCode.BadRequest, new
                        {
                            error = $"Filter '{key}' requires at least one value."
                        });
                    }

                    var parameterNames = new List<string>();
                    foreach (var item in items)
                    {
                        var parameterName = $"@p{parameterIndex++}";
                        parameterNames.Add(parameterName);
                        sqlParameters.Add(new SqlParameter(parameterName, ConvertValue(sqlDataType, item)));
                    }

                    whereClauses.Add($"{QuoteIdentifier(columnName)} IN ({string.Join(", ", parameterNames)})");
                    continue;
                }

                if (!OperatorMap.TryGetValue(op, out var sqlOperator))
                {
                    return await CreateJsonResponseAsync(req, HttpStatusCode.BadRequest, new
                    {
                        error = $"Unsupported operator '{op}' for filter '{key}'."
                    });
                }

                var parameter = $"@p{parameterIndex++}";
                var parameterValue = string.Equals(op, "like", StringComparison.OrdinalIgnoreCase)
                    ? rawValue
                    : ConvertValue(sqlDataType, rawValue);

                sqlParameters.Add(new SqlParameter(parameter, parameterValue));
                whereClauses.Add($"{QuoteIdentifier(columnName)} {sqlOperator} {parameter}");
            }
        }

        var qualifiedTable = $"{QuoteIdentifier(schemaName)}.{QuoteIdentifier(tableName)}";
        var sql = new StringBuilder();

        if (offset == 0)
        {
            sql.Append($"SELECT TOP (@limit) * FROM {qualifiedTable}");
        }
        else
        {
            sql.Append($"SELECT * FROM {qualifiedTable}");
        }

        if (whereClauses.Count > 0)
        {
            sql.Append(" WHERE ");
            sql.Append(string.Join(" AND ", whereClauses));
        }

        sql.Append($" ORDER BY {QuoteIdentifier(sortBy)} {sortDir}");

        if (offset > 0)
        {
            sql.Append(" OFFSET @offset ROWS FETCH NEXT @limit ROWS ONLY");
        }

        await using var command = new SqlCommand(sql.ToString(), connection);
        command.Parameters.Add(new SqlParameter("@limit", limit));

        if (offset > 0)
        {
            command.Parameters.Add(new SqlParameter("@offset", offset));
        }

        foreach (var parameter in sqlParameters)
        {
            command.Parameters.Add(parameter);
        }

        var rows = new List<Dictionary<string, object?>>();
        await using var reader = await command.ExecuteReaderAsync();

        while (await reader.ReadAsync())
        {
            var row = new Dictionary<string, object?>(reader.FieldCount, StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < reader.FieldCount; i++)
            {
                var value = reader.GetValue(i);
                row[reader.GetName(i)] = value == DBNull.Value ? null : value;
            }

            rows.Add(row);
        }

        return await CreateJsonResponseAsync(req, HttpStatusCode.OK, new
        {
            schema = schemaName,
            table = tableName,
            count = rows.Count,
            limit,
            offset,
            sortBy,
            sortDir,
            data = rows
        });
    }

    private static async Task<Dictionary<string, string>> GetColumnTypesAsync(SqlConnection connection, string schemaName, string tableName)
    {
        const string sql = @"
SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = @schemaName
  AND TABLE_NAME = @tableName
ORDER BY ORDINAL_POSITION;";

        var columns = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        await using var command = new SqlCommand(sql, connection);
        command.Parameters.Add(new SqlParameter("@schemaName", schemaName));
        command.Parameters.Add(new SqlParameter("@tableName", tableName));

        await using var reader = await command.ExecuteReaderAsync();
        while (await reader.ReadAsync())
        {
            columns[reader.GetString(0)] = reader.GetString(1);
        }

        return columns;
    }

    private static (string ColumnName, string Operator) ParseFilterKey(string key)
    {
        var parts = key.Split(new[] { "__" }, StringSplitOptions.None);
        if (parts.Length == 2 && !string.IsNullOrWhiteSpace(parts[0]) && !string.IsNullOrWhiteSpace(parts[1]))
        {
            return (parts[0], parts[1]);
        }

        return (key, "eq");
    }

    private static object ConvertValue(string sqlDataType, string rawValue)
    {
        switch (sqlDataType.ToLowerInvariant())
        {
            case "bigint":
                return long.Parse(rawValue, CultureInfo.InvariantCulture);

            case "int":
                return int.Parse(rawValue, CultureInfo.InvariantCulture);

            case "smallint":
                return short.Parse(rawValue, CultureInfo.InvariantCulture);

            case "tinyint":
                return byte.Parse(rawValue, CultureInfo.InvariantCulture);

            case "bit":
                return rawValue switch
                {
                    "1" => true,
                    "0" => false,
                    _ => bool.Parse(rawValue)
                };

            case "decimal":
            case "numeric":
            case "money":
            case "smallmoney":
                return decimal.Parse(rawValue, CultureInfo.InvariantCulture);

            case "float":
                return double.Parse(rawValue, CultureInfo.InvariantCulture);

            case "real":
                return float.Parse(rawValue, CultureInfo.InvariantCulture);

            case "date":
            case "datetime":
            case "datetime2":
            case "smalldatetime":
                return DateTime.Parse(rawValue, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind);

            case "datetimeoffset":
                return DateTimeOffset.Parse(rawValue, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind);

            case "time":
                return TimeSpan.Parse(rawValue, CultureInfo.InvariantCulture);

            case "uniqueidentifier":
                return Guid.Parse(rawValue);

            default:
                return rawValue;
        }
    }

    private static int ParseInt(string? rawValue, int defaultValue, int min, int max)
    {
        if (!int.TryParse(rawValue, NumberStyles.Integer, CultureInfo.InvariantCulture, out var parsed))
        {
            return defaultValue;
        }

        if (parsed < min)
        {
            return min;
        }

        if (parsed > max)
        {
            return max;
        }

        return parsed;
    }

    private static bool IsSafeIdentifier(string value) => SafeIdentifier.IsMatch(value);

    private static string QuoteIdentifier(string identifier) => $"[{identifier}]";

    private static async Task<HttpResponseData> CreateJsonResponseAsync(HttpRequestData req, HttpStatusCode statusCode, object payload)
    {
        var response = req.CreateResponse(statusCode);
        response.Headers.Add("Content-Type", "application/json; charset=utf-8");
        await response.WriteStringAsync(JsonSerializer.Serialize(payload));
        return response;
    }
}