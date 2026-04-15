using System.Text;
using Microsoft.Azure.Functions.Worker.Http;
using Microsoft.Extensions.Logging;

namespace DebugLoggingFunction;

public static class RequestLogging
{
    private static readonly HashSet<string> SensitiveHeaderNames = new(StringComparer.OrdinalIgnoreCase)
    {
        "Authorization",
        "Cookie",
        "Set-Cookie",
        "X-Api-Key",
        "X-Functions-Key",
        "Proxy-Authorization"
    };

    public static async Task<string> ReadBodyAsync(HttpRequestData req, ILogger logger, CancellationToken cancellationToken)
    {
        using var reader = new StreamReader(req.Body, Encoding.UTF8);
        var body = await reader.ReadToEndAsync(cancellationToken).ConfigureAwait(false);
        logger.LogInformation("HTTP request body length={Length} content={Body}", body.Length, body);
        return body;
    }

    public static void LogAllHeaders(HttpRequestData req, ILogger logger)
    {
        foreach (var kv in req.Headers)
        {
            var name = kv.Key;
            var values = string.Join(", ", kv.Value);
            if (SensitiveHeaderNames.Contains(name))
            {
                logger.LogInformation("HTTP header {HeaderName}: [REDACTED] length={Length} preview={Preview}", name, values.Length, MaskForLog(values));
            }
            else
            {
                logger.LogInformation("HTTP header {HeaderName}: {HeaderValue}", name, values);
            }
        }
    }

    public static void LogUserContext(HttpRequestData req, ILogger logger)
    {
        if (req.Headers.TryGetValues("X-MS-CLIENT-PRINCIPAL-NAME", out var names))
        {
            logger.LogInformation("User principal name: {Name}", string.Join(", ", names));
        }

        if (req.Headers.TryGetValues("X-MS-CLIENT-PRINCIPAL-ID", out var ids))
        {
            logger.LogInformation("User principal id: {Id}", string.Join(", ", ids));
        }

        if (req.Headers.TryGetValues("X-Forwarded-For", out var xff))
        {
            logger.LogInformation("X-Forwarded-For: {Xff}", string.Join(", ", xff));
        }
    }

    private static string MaskForLog(string value)
    {
        if (string.IsNullOrEmpty(value)) return string.Empty;
        var span = value.Length <= 8 ? value : value.AsSpan(0, 4).ToString() + "..." + value.AsSpan(value.Length - 4).ToString();
        return span;
    }
}
