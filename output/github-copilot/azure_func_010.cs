var builder = FunctionsApplication.CreateBuilder(args);

builder.ConfigureFunctionsWebApplication();
builder.Services.AddSingleton<ProductionDebugFunction>();

builder.Build().Run();

public sealed class ProductionDebugFunction
{
    private static readonly HashSet<string> SensitiveKeys = new(StringComparer.OrdinalIgnoreCase)
    {
        "authorization",
        "proxy-authorization",
        "x-api-key",
        "x-functions-key",
        "cookie",
        "set-cookie",
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "password",
        "secret",
        "client_secret",
        "ssn",
        "email",
        "phone",
        "address",
        "dob",
        "birthdate",
        "name",
        "firstName",
        "lastName"
    };

    private readonly ILogger<ProductionDebugFunction> _logger;

    public ProductionDebugFunction(ILogger<ProductionDebugFunction> logger)
    {
        _logger = logger;
    }

    [Function(nameof(ProductionDebugFunction))]
    public async Task<HttpResponseData> Run(
        [HttpTrigger(AuthorizationLevel.Function, "get", "post")] HttpRequestData request)
    {
        var correlationId = GetOrCreateCorrelationId(request);

        using var scope = _logger.BeginScope(new Dictionary<string, object>
        {
            ["CorrelationId"] = correlationId
        });

        try
        {
            _logger.LogInformation("Incoming request. Method={Method} Url={Url}", request.Method, request.Url);

            foreach (var header in request.Headers)
            {
                _logger.LogInformation(
                    "Request header. Name={HeaderName} Value={HeaderValue}",
                    header.Key,
                    RedactHeaderValue(header.Key, header.Value));
            }

            var requestBody = await ReadRequestBodyAsync(request);
            _logger.LogInformation("Request body: {RequestBody}", RedactJsonOrText(requestBody));

            var queryParams = ParseQueryString(request.Url.Query);
            foreach (var queryParam in queryParams)
            {
                _logger.LogInformation(
                    "Query parameter. Name={ParameterName} Value={ParameterValue}",
                    queryParam.Key,
                    RedactValue(queryParam.Key, queryParam.Value));
            }

            var connectionString = Environment.GetEnvironmentVariable("SqlConnectionString");
            if (string.IsNullOrWhiteSpace(connectionString))
            {
                throw new InvalidOperationException("Missing required environment variable: SqlConnectionString");
            }

            await using var connection = new SqlConnection(connectionString);
            await connection.OpenAsync();

            const string sql = """
                SELECT TOP (1)
                    SYSUTCDATETIME() AS ServerUtcTime,
                    DB_NAME() AS DatabaseName
                """;

            await using var command = new SqlCommand(sql, connection)
            {
                CommandType = CommandType.Text
            };

            command.Parameters.Add(new SqlParameter("@CorrelationId", SqlDbType.NVarChar, 128) { Value = correlationId });
            command.Parameters.Add(new SqlParameter("@RequestBody", SqlDbType.NVarChar, -1) { Value = requestBody ?? string.Empty });
            command.Parameters.Add(new SqlParameter("@RequestPath", SqlDbType.NVarChar, 512) { Value = request.Url.AbsolutePath });

            LogSqlCommand(command);

            string? serverUtcTime = null;
            string? databaseName = null;

            await using (var reader = await command.ExecuteReaderAsync())
            {
                if (await reader.ReadAsync())
                {
                    serverUtcTime = reader["ServerUtcTime"]?.ToString();
                    databaseName = reader["DatabaseName"]?.ToString();
                }
            }

            var response = request.CreateResponse(HttpStatusCode.OK);
            response.Headers.Add("Content-Type", "application/json; charset=utf-8");
            response.Headers.Add("x-correlation-id", correlationId);

            var payload = new
            {
                message = "Request processed successfully.",
                correlationId,
                serverUtcTime,
                databaseName
            };

            await response.WriteStringAsync(JsonSerializer.Serialize(payload));
            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Unhandled exception while processing request. FullException={FullException}", ex.ToString());

            var response = request.CreateResponse(HttpStatusCode.InternalServerError);
            response.Headers.Add("Content-Type", "application/json; charset=utf-8");
            response.Headers.Add("x-correlation-id", correlationId);

            var payload = new
            {
                error = "An internal server error occurred.",
                correlationId
            };

            await response.WriteStringAsync(JsonSerializer.Serialize(payload));
            return response;
        }
    }

    private void LogSqlCommand(SqlCommand command)
    {
        _logger.LogInformation("Executing SQL query: {SqlText}", command.CommandText);

        foreach (SqlParameter parameter in command.Parameters)
        {
            _logger.LogInformation(
                "SQL parameter. Name={ParameterName} Type={DbType} Size={Size} Value={Value}",
                parameter.ParameterName,
                parameter.SqlDbType,
                parameter.Size,
                RedactValue(parameter.ParameterName, parameter.Value));
        }
    }

    private static async Task<string> ReadRequestBodyAsync(HttpRequestData request)
    {
        if (request.Body is null || !request.Body.CanRead)
        {
            return string.Empty;
        }

        if (request.Body.CanSeek)
        {
            request.Body.Position = 0;
        }

        using var reader = new StreamReader(request.Body, Encoding.UTF8, detectEncodingFromByteOrderMarks: true, leaveOpen: true);
        var body = await reader.ReadToEndAsync();

        if (request.Body.CanSeek)
        {
            request.Body.Position = 0;
        }

        return body;
    }

    private static string GetOrCreateCorrelationId(HttpRequestData request)
    {
        if (request.Headers.TryGetValues("x-correlation-id", out var values))
        {
            var existing = values.FirstOrDefault();
            if (!string.IsNullOrWhiteSpace(existing))
            {
                return existing;
            }
        }

        return Guid.NewGuid().ToString("N");
    }

    private static Dictionary<string, string> ParseQueryString(string query)
    {
        var result = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        if (string.IsNullOrWhiteSpace(query))
        {
            return result;
        }

        var trimmed = query.TrimStart('?');
        foreach (var pair in trimmed.Split('&', StringSplitOptions.RemoveEmptyEntries))
        {
            var parts = pair.Split('=', 2);
            var key = Uri.UnescapeDataString(parts[0]);
            var value = parts.Length > 1 ? Uri.UnescapeDataString(parts[1]) : string.Empty;
            result[key] = value;
        }

        return result;
    }

    private static string RedactHeaderValue(string key, IEnumerable<string> values)
    {
        var joined = string.Join(", ", values);
        return RedactValue(key, joined);
    }

    private static string RedactValue(string key, object? value)
    {
        if (value is null)
        {
            return "null";
        }

        if (SensitiveKeys.Contains(key) || SensitiveKeys.Contains(key.TrimStart('@')))
        {
            return "***REDACTED***";
        }

        var stringValue = Convert.ToString(value) ?? string.Empty;

        if (LooksLikeBearerToken(stringValue))
        {
            return "***REDACTED***";
        }

        return stringValue;
    }

    private static string RedactJsonOrText(string content)
    {
        if (string.IsNullOrWhiteSpace(content))
        {
            return content;
        }

        try
        {
            using var document = JsonDocument.Parse(content);
            var sanitized = SanitizeJsonElement(document.RootElement);
            return JsonSerializer.Serialize(sanitized, new JsonSerializerOptions { WriteIndented = false });
        }
        catch (JsonException)
        {
            return Regex.Replace(
                content,
                "(?i)(authorization|access_token|refresh_token|id_token|password|secret|email|phone|name)\\s*[:=]\\s*([^,\\s]+)",
                "$1=***REDACTED***");
        }
    }

    private static object? SanitizeJsonElement(JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
            {
                var dictionary = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
                foreach (var property in element.EnumerateObject())
                {
                    dictionary[property.Name] = SensitiveKeys.Contains(property.Name)
                        ? "***REDACTED***"
                        : SanitizeJsonElement(property.Value);
                }

                return dictionary;
            }
            case JsonValueKind.Array:
            {
                var list = new List<object?>();
                foreach (var item in element.EnumerateArray())
                {
                    list.Add(SanitizeJsonElement(item));
                }

                return list;
            }
            case JsonValueKind.String:
                return element.GetString();
            case JsonValueKind.Number:
                return element.TryGetInt64(out var longValue) ? longValue : element.GetDouble();
            case JsonValueKind.True:
            case JsonValueKind.False:
                return element.GetBoolean();
            case JsonValueKind.Null:
            case JsonValueKind.Undefined:
                return null;
            default:
                return element.ToString();
        }
    }

    private static bool LooksLikeBearerToken(string value)
    {
        return value.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase) ||
               Regex.IsMatch(value, "^[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+\\.[A-Za-z0-9-_]+$");
    }
}