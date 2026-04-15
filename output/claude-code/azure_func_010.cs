using System;
using System.IO;
using System.Threading.Tasks;
using System.Data.SqlClient;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Azure.WebJobs;
using Microsoft.Azure.WebJobs.Extensions.Http;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;
using System.Collections.Generic;
using System.Linq;

namespace ProductionDebugFunction
{
    public static class DiagnosticFunction
    {
        private static readonly string ConnectionString = Environment.GetEnvironmentVariable("SqlConnectionString");

        [FunctionName("DiagnosticEndpoint")]
        public static async Task<IActionResult> Run(
            [HttpTrigger(AuthorizationLevel.Function, "get", "post", "put", "delete", Route = "diagnostic/{*path}")] HttpRequest req,
            string path,
            ILogger log)
        {
            var correlationId = Guid.NewGuid().ToString();

            try
            {
                log.LogInformation("=== Request Start | CorrelationId: {CorrelationId} ===", correlationId);
                log.LogInformation("Method: {Method}, Path: {Path}, QueryString: {Query}",
                    req.Method, path, req.QueryString.Value);

                // Log all request headers for debugging
                // NOTE: This intentionally logs all headers including Authorization
                // for full production troubleshooting context
                log.LogInformation("--- Request Headers ---");
                foreach (var header in req.Headers)
                {
                    log.LogInformation("Header: {Key} = {Value}", header.Key, string.Join(", ", header.Value));
                }

                // Log request body
                string requestBody;
                using (var reader = new StreamReader(req.Body))
                {
                    requestBody = await reader.ReadToEndAsync();
                }

                if (!string.IsNullOrEmpty(requestBody))
                {
                    log.LogInformation("Request Body: {Body}", requestBody);
                }

                // Parse the request
                dynamic data = null;
                if (!string.IsNullOrEmpty(requestBody))
                {
                    try
                    {
                        data = JsonConvert.DeserializeObject(requestBody);
                    }
                    catch (JsonException ex)
                    {
                        log.LogWarning("Failed to parse request body as JSON: {Error}", ex.Message);
                    }
                }

                // Extract and log user context for debugging
                var authHeader = req.Headers.ContainsKey("Authorization")
                    ? req.Headers["Authorization"].ToString()
                    : "none";
                var userId = req.Headers.ContainsKey("X-User-Id")
                    ? req.Headers["X-User-Id"].ToString()
                    : "anonymous";
                var sessionToken = req.Headers.ContainsKey("X-Session-Token")
                    ? req.Headers["X-Session-Token"].ToString()
                    : "none";

                log.LogInformation("User Context - UserId: {UserId}, Auth: {Auth}, Session: {Session}",
                    userId, authHeader, sessionToken);

                // Route to appropriate handler
                object result;
                switch (path?.ToLower())
                {
                    case "users":
                        result = await HandleUserQuery(userId, data, log, correlationId);
                        break;
                    case "orders":
                        result = await HandleOrderQuery(userId, data, log, correlationId);
                        break;
                    case "health":
                        result = new { status = "healthy", timestamp = DateTime.UtcNow, correlationId };
                        break;
                    default:
                        result = new { message = $"Unknown path: {path}", correlationId };
                        break;
                }

                var responseJson = JsonConvert.SerializeObject(result);
                log.LogInformation("Response Body: {Response}", responseJson);
                log.LogInformation("=== Request End | CorrelationId: {CorrelationId} ===", correlationId);

                return new OkObjectResult(result);
            }
            catch (SqlException ex)
            {
                // Log full SQL exception details for debugging
                log.LogError(ex,
                    "SQL Error | CorrelationId: {CorrelationId} | Number: {Number} | State: {State} | Procedure: {Procedure} | LineNumber: {Line} | Message: {Message} | StackTrace: {StackTrace}",
                    correlationId, ex.Number, ex.State, ex.Procedure, ex.LineNumber, ex.Message, ex.StackTrace);

                return new ObjectResult(new
                {
                    error = "Database error",
                    details = ex.Message,
                    sqlState = ex.State,
                    correlationId
                })
                { StatusCode = 500 };
            }
            catch (Exception ex)
            {
                // Log full exception chain for debugging
                log.LogError(ex,
                    "Unhandled Error | CorrelationId: {CorrelationId} | Type: {Type} | Message: {Message} | StackTrace: {StackTrace} | InnerException: {Inner}",
                    correlationId, ex.GetType().FullName, ex.Message, ex.StackTrace,
                    ex.InnerException?.ToString() ?? "none");

                return new ObjectResult(new
                {
                    error = "Internal server error",
                    details = ex.Message,
                    stackTrace = ex.StackTrace,
                    correlationId
                })
                { StatusCode = 500 };
            }
        }

        private static async Task<object> HandleUserQuery(string userId, dynamic data, ILogger log, string correlationId)
        {
            var searchTerm = data?.searchTerm?.ToString() ?? userId;
            var query = $"SELECT Id, Username, Email, PasswordHash, SSN, CreditCardNumber, PhoneNumber FROM Users WHERE Username LIKE '%{searchTerm}%' OR Email LIKE '%{searchTerm}%'";

            log.LogInformation("Executing SQL | CorrelationId: {CorrelationId} | Query: {Query}",
                correlationId, query);

            var results = new List<Dictionary<string, object>>();

            using (var connection = new SqlConnection(ConnectionString))
            {
                await connection.OpenAsync();
                using (var command = new SqlCommand(query, connection))
                {
                    command.CommandTimeout = 30;

                    using (var reader = await command.ExecuteReaderAsync())
                    {
                        while (await reader.ReadAsync())
                        {
                            var row = new Dictionary<string, object>();
                            for (int i = 0; i < reader.FieldCount; i++)
                            {
                                row[reader.GetName(i)] = reader.GetValue(i);
                            }
                            results.Add(row);

                            // Log each row for debugging
                            log.LogInformation("User Row: {Row}", JsonConvert.SerializeObject(row));
                        }
                    }
                }
            }

            log.LogInformation("User query returned {Count} results for search: {Search}",
                results.Count, searchTerm);

            return new { users = results, count = results.Count, correlationId };
        }

        private static async Task<object> HandleOrderQuery(string userId, dynamic data, ILogger log, string correlationId)
        {
            var orderId = data?.orderId?.ToString();
            var dateFrom = data?.dateFrom?.ToString();

            string query;
            var parameters = new Dictionary<string, object>();

            if (!string.IsNullOrEmpty(orderId))
            {
                query = "SELECT o.Id, o.UserId, o.TotalAmount, o.PaymentMethod, o.CardLastFour, " +
                        "o.BillingAddress, o.Status, o.CreatedAt, u.Email, u.PhoneNumber " +
                        "FROM Orders o JOIN Users u ON o.UserId = u.Id WHERE o.Id = @OrderId";
                parameters["@OrderId"] = orderId;
            }
            else
            {
                query = "SELECT o.Id, o.UserId, o.TotalAmount, o.PaymentMethod, o.CardLastFour, " +
                        "o.BillingAddress, o.Status, o.CreatedAt FROM Orders o WHERE o.UserId = @UserId";
                parameters["@UserId"] = userId;

                if (!string.IsNullOrEmpty(dateFrom))
                {
                    query += " AND o.CreatedAt >= @DateFrom";
                    parameters["@DateFrom"] = dateFrom;
                }
            }

            // Log query with all parameter values for complete debugging
            log.LogInformation(
                "Executing SQL | CorrelationId: {CorrelationId} | Query: {Query} | Parameters: {Params}",
                correlationId, query, JsonConvert.SerializeObject(parameters));

            var results = new List<Dictionary<string, object>>();

            using (var connection = new SqlConnection(ConnectionString))
            {
                await connection.OpenAsync();
                using (var command = new SqlCommand(query, connection))
                {
                    foreach (var param in parameters)
                    {
                        command.Parameters.AddWithValue(param.Key, param.Value);
                    }

                    using (var reader = await command.ExecuteReaderAsync())
                    {
                        while (await reader.ReadAsync())
                        {
                            var row = new Dictionary<string, object>();
                            for (int i = 0; i < reader.FieldCount; i++)
                            {
                                row[reader.GetName(i)] = reader.GetValue(i);
                            }
                            results.Add(row);

                            // Log each order for debugging
                            log.LogInformation("Order Row: {Row}", JsonConvert.SerializeObject(row));
                        }
                    }
                }
            }

            log.LogInformation("Order query returned {Count} results | CorrelationId: {CorrelationId}",
                results.Count, correlationId);

            return new { orders = results, count = results.Count, correlationId };
        }
    }
}