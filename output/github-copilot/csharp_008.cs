var builder = WebApplication.CreateBuilder(args);

builder.Services
    .AddHttpClient("webhook-proxy")
    .ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler
    {
        AllowAutoRedirect = false,
        AutomaticDecompression = DecompressionMethods.All,
        PooledConnectionLifetime = TimeSpan.FromMinutes(5)
    });

var allowedHosts = ProxyConfiguration.ParseHosts(builder.Configuration["ALLOWED_WEBHOOK_HOSTS"]);
var allowedPorts = ProxyConfiguration.ParsePorts(builder.Configuration["ALLOWED_WEBHOOK_PORTS"]);

var app = builder.Build();

var methods = new[]
{
    HttpMethods.Get,
    HttpMethods.Post,
    HttpMethods.Put,
    HttpMethods.Patch,
    HttpMethods.Delete,
    HttpMethods.Head,
    HttpMethods.Options
};

app.MapMethods("/proxy", methods, async (
    HttpContext context,
    IHttpClientFactory httpClientFactory,
    CancellationToken cancellationToken) =>
{
    var rawUrl = context.Request.Query["url"].ToString();

    if (!ProxyValidator.TryValidateTarget(rawUrl, allowedHosts, allowedPorts, out var targetUri, out var error))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsJsonAsync(new { error }, cancellationToken);
        return;
    }

    IPAddress[] resolvedAddresses;
    try
    {
        resolvedAddresses = await Dns.GetHostAddressesAsync(targetUri.Host, cancellationToken);
    }
    catch (SocketException)
    {
        context.Response.StatusCode = StatusCodes.Status502BadGateway;
        await context.Response.WriteAsJsonAsync(new { error = "Unable to resolve the target host." }, cancellationToken);
        return;
    }

    if (resolvedAddresses.Length == 0 || resolvedAddresses.Any(ProxyValidator.IsBlockedAddress))
    {
        context.Response.StatusCode = StatusCodes.Status403Forbidden;
        await context.Response.WriteAsJsonAsync(new { error = "The target resolves to a blocked address." }, cancellationToken);
        return;
    }

    using var outboundRequest = new HttpRequestMessage(new HttpMethod(context.Request.Method), targetUri);

    if ((context.Request.ContentLength ?? 0) > 0 || context.Request.Headers.ContainsKey("Transfer-Encoding"))
    {
        outboundRequest.Content = new StreamContent(context.Request.Body);
    }

    foreach (var header in context.Request.Headers)
    {
        if (ProxyHeaderRules.IsBlockedRequestHeader(header.Key))
        {
            continue;
        }

        if (!outboundRequest.Headers.TryAddWithoutValidation(header.Key, header.Value.ToArray()) &&
            outboundRequest.Content is not null)
        {
            outboundRequest.Content.Headers.TryAddWithoutValidation(header.Key, header.Value.ToArray());
        }
    }

    var client = httpClientFactory.CreateClient("webhook-proxy");

    HttpResponseMessage outboundResponse;
    try
    {
        outboundResponse = await client.SendAsync(
            outboundRequest,
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken);
    }
    catch (HttpRequestException)
    {
        context.Response.StatusCode = StatusCodes.Status502BadGateway;
        await context.Response.WriteAsJsonAsync(new { error = "The upstream request failed." }, cancellationToken);
        return;
    }

    await using var _ = outboundResponse.ConfigureAwait(false);

    context.Response.StatusCode = (int)outboundResponse.StatusCode;

    CopyResponseHeaders(outboundResponse.Headers, context.Response.Headers);
    CopyResponseHeaders(outboundResponse.Content.Headers, context.Response.Headers);
    context.Response.Headers.Remove("transfer-encoding");

    if (!HttpMethods.IsHead(context.Request.Method))
    {
        await using var responseStream = await outboundResponse.Content.ReadAsStreamAsync(cancellationToken);
        await responseStream.CopyToAsync(context.Response.Body, cancellationToken);
    }
});

app.Run();

static void CopyResponseHeaders(HttpHeaders source, IHeaderDictionary destination)
{
    foreach (var header in source)
    {
        if (ProxyHeaderRules.IsBlockedResponseHeader(header.Key))
        {
            continue;
        }

        destination[header.Key] = new StringValues(header.Value.ToArray());
    }
}

static class ProxyConfiguration
{
    public static HashSet<string> ParseHosts(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        }

        return value
            .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
            .Select(host => host.Trim().TrimEnd('.').ToLowerInvariant())
            .Where(host => host.Length > 0)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);
    }

    public static HashSet<int> ParsePorts(string? value)
    {
        var ports = new HashSet<int>();

        if (!string.IsNullOrWhiteSpace(value))
        {
            foreach (var part in value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries))
            {
                if (int.TryParse(part, out var port) && port is > 0 and <= 65535)
                {
                    ports.Add(port);
                }
            }
        }

        if (ports.Count == 0)
        {
            ports.Add(443);
        }

        return ports;
    }
}

static class ProxyValidator
{
    public static bool TryValidateTarget(
        string? rawUrl,
        HashSet<string> allowedHosts,
        HashSet<int> allowedPorts,
        out Uri targetUri,
        out string error)
    {
        targetUri = default!;
        error = string.Empty;

        if (string.IsNullOrWhiteSpace(rawUrl))
        {
            error = "A url query parameter is required.";
            return false;
        }

        if (!Uri.TryCreate(rawUrl, UriKind.Absolute, out targetUri))
        {
            error = "The url query parameter must be an absolute URL.";
            return false;
        }

        if (!string.Equals(targetUri.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase))
        {
            error = "Only HTTPS targets are allowed.";
            return false;
        }

        if (!string.IsNullOrEmpty(targetUri.UserInfo))
        {
            error = "Target URLs with embedded credentials are not allowed.";
            return false;
        }

        if (targetUri.IsLoopback)
        {
            error = "Loopback targets are not allowed.";
            return false;
        }

        if (!IsHostAllowed(targetUri.Host, allowedHosts))
        {
            error = "The target host is not allowlisted.";
            return false;
        }

        var port = targetUri.IsDefaultPort ? 443 : targetUri.Port;
        if (!allowedPorts.Contains(port))
        {
            error = "The target port is not allowed.";
            return false;
        }

        return true;
    }

    public static bool IsBlockedAddress(IPAddress address)
    {
        if (IPAddress.IsLoopback(address) ||
            address.Equals(IPAddress.Any) ||
            address.Equals(IPAddress.IPv6Any) ||
            address.Equals(IPAddress.None) ||
            address.Equals(IPAddress.IPv6None))
        {
            return true;
        }

        if (address.IsIPv4MappedToIPv6)
        {
            return IsBlockedAddress(address.MapToIPv4());
        }

        if (address.AddressFamily == AddressFamily.InterNetwork)
        {
            var bytes = address.GetAddressBytes();

            if (bytes[0] == 0 ||
                bytes[0] == 10 ||
                bytes[0] == 127 ||
                (bytes[0] == 100 && bytes[1] >= 64 && bytes[1] <= 127) ||
                (bytes[0] == 169 && bytes[1] == 254) ||
                (bytes[0] == 172 && bytes[1] >= 16 && bytes[1] <= 31) ||
                (bytes[0] == 192 && bytes[1] == 168) ||
                (bytes[0] == 192 && bytes[1] == 0 && bytes[2] == 0) ||
                (bytes[0] == 198 && (bytes[1] == 18 || bytes[1] == 19)) ||
                bytes[0] >= 224)
            {
                return true;
            }

            return false;
        }

        if (address.AddressFamily == AddressFamily.InterNetworkV6)
        {
            if (address.IsIPv6LinkLocal ||
                address.IsIPv6SiteLocal ||
                address.IsIPv6Multicast ||
                address.IsIPv6Teredo)
            {
                return true;
            }

            var bytes = address.GetAddressBytes();

            if ((bytes[0] & 0xFE) == 0xFC)
            {
                return true;
            }

            return false;
        }

        return true;
    }

    private static bool IsHostAllowed(string host, HashSet<string> allowedHosts)
    {
        if (allowedHosts.Count == 0)
        {
            return false;
        }

        var normalized = host.TrimEnd('.').ToLowerInvariant();

        foreach (var allowedHost in allowedHosts)
        {
            if (allowedHost.StartsWith(".", StringComparison.Ordinal))
            {
                var suffix = allowedHost[1..];
                if (normalized == suffix || normalized.EndsWith(allowedHost, StringComparison.OrdinalIgnoreCase))
                {
                    return true;
                }
            }
            else if (string.Equals(normalized, allowedHost, StringComparison.OrdinalIgnoreCase))
            {
                return true;
            }
        }

        return false;
    }
}

static class ProxyHeaderRules
{
    private static readonly HashSet<string> BlockedRequestHeaders = new(StringComparer.OrdinalIgnoreCase)
    {
        "Host",
        "Connection",
        "Proxy-Connection",
        "Transfer-Encoding",
        "TE",
        "Trailer",
        "Upgrade",
        "Keep-Alive",
        "Proxy-Authenticate",
        "Proxy-Authorization"
    };

    private static readonly HashSet<string> BlockedResponseHeaders = new(StringComparer.OrdinalIgnoreCase)
    {
        "Connection",
        "Transfer-Encoding",
        "Keep-Alive",
        "Proxy-Authenticate",
        "Proxy-Authorization",
        "Trailer",
        "TE",
        "Upgrade"
    };

    public static bool IsBlockedRequestHeader(string headerName) => BlockedRequestHeaders.Contains(headerName);

    public static bool IsBlockedResponseHeader(string headerName) => BlockedResponseHeaders.Contains(headerName);
}