using System.Net;
using System.Text.Json;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Data.SqlClient;
using Microsoft.Extensions.Logging;

namespace DebugLoggingFunction;

public class DebugHttpFunction
{
    private readonly ILogger<DebugHttpFunction> _logger;

    public DebugHttpFunction(ILogger<DebugHttpFunction> logger)
    {
        _logger = logger;
    }

    [Function(nameof(DebugHttp))]
    public async Task<HttpResponseData> DebugHttp(
        [HttpTrigger(AuthorizationLevel.Function, "get", "post", Route = "debug")] HttpRequestData req,
        FunctionContext context,
        CancellationToken cancellationToken)
    {
        _logger.LogInformation("Function invocation id={InvocationId}", context.InvocationId);

        try
        {
            RequestLogging.LogAllHeaders(req, _logger);
            RequestLogging.LogUserContext(req, _logger);

            var body = string.Empty;
            if (req.Body != null && req.Body.CanRead)
            {
                body = await RequestLogging.ReadBodyAsync(req, _logger, cancellationToken).ConfigureAwait(false);
            }

            var connectionString = Environment.GetEnvironmentVariable("SqlConnectionString");
            if (!string.IsNullOrEmpty(connectionString))
            {
                var parameters = new List<SqlParameter>
                {
                    new("@Sample", body.Length)
                };

                try
                {
                    await SqlLogging.ExecuteNonQueryWithLoggingAsync(
                        connectionString,
                        "SELECT @Sample AS SampleLen",
                        parameters,
                        _logger,
                        cancellationToken).ConfigureAwait(false);
                }
                catch (SqlException ex)
                {
                    _logger.LogError(
                        ex,
                        "Database error Number={Number} State={State} Class={Class} Server={Server} Procedure={Procedure} LineNumber={Line}",
                        ex.Number,
                        ex.State,
                        ex.Class,
                        ex.Server,
                        ex.Procedure,
                        ex.LineNumber);
                    throw;
                }
            }
            else
            {
                _logger.LogWarning("SqlConnectionString not set; skipping database call.");
            }

            var response = req.CreateResponse(HttpStatusCode.OK);
            response.Headers.Add("Content-Type", "application/json; charset=utf-8");
            await response.WriteStringAsync(JsonSerializer.Serialize(new { ok = true, bodyLength = body.Length }), cancellationToken).ConfigureAwait(false);
            return response;
        }
        catch (Exception ex)
        {
            _logger.LogError(
                ex,
                "Unhandled exception type={Type} message={Message} stack={Stack}",
                ex.GetType().FullName,
                ex.Message,
                ex.StackTrace);

            if (ex.InnerException != null)
            {
                _logger.LogError(
                    ex.InnerException,
                    "Inner exception type={Type} message={Message} stack={Stack}",
                    ex.InnerException.GetType().FullName,
                    ex.InnerException.Message,
                    ex.InnerException.StackTrace);
            }

            var err = req.CreateResponse(HttpStatusCode.InternalServerError);
            err.Headers.Add("Content-Type", "application/json; charset=utf-8");
            await err.WriteStringAsync(JsonSerializer.Serialize(new { error = "failed", detail = ex.Message }), cancellationToken).ConfigureAwait(false);
            return err;
        }
    }
}
