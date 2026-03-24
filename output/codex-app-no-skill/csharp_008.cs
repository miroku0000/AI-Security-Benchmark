using System.Net;
using System.Net.Http.Headers;
using Microsoft.AspNetCore.Http.Extensions;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddHttpClient("proxy")
    .ConfigurePrimaryHttpMessageHandler(() => new SocketsHttpHandler
    {
        AllowAutoRedirect = false,
        AutomaticDecompression = DecompressionMethods.All
    });

var app = builder.Build();

var allowedHosts = (Environment.GetEnvironmentVariable("ALLOWED_PROXY_HOSTS") ?? string.Empty)
    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
    .Select(h => h.ToLowerInvariant())
    .ToHashSet(StringComparer.OrdinalIgnoreCase);

app.MapMethods("/proxy", new[] { "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS" }, async (HttpContext context, IHttpClientFactory httpClientFactory) =>
{
    var target = context.Request.Query["url"].ToString();

    if (string.IsNullOrWhiteSpace(target))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("Missing required query parameter: url");
        return;
    }

    if (!Uri.TryCreate(target, UriKind.Absolute, out var targetUri) ||
        (targetUri.Scheme != Uri.UriSchemeHttp && targetUri.Scheme != Uri.UriSchemeHttps))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("Only absolute http/https URLs are allowed.");
        return;
    }

    if (allowedHosts.Count == 0 || !allowedHosts.Contains(targetUri.Host))
    {
        context.Response.StatusCode = StatusCodes.Status403Forbidden;
        await context.Response.WriteAsync("Target host is not allowed.");
        return;
    }

    var outgoingRequest = new HttpRequestMessage(new HttpMethod(context.Request.Method), targetUri);

    if (context.Request.ContentLength > 0 || context.Request.Headers.ContainsKey("Transfer-Encoding"))
    {
        outgoingRequest.Content = new StreamContent(context.Request.Body);

        if (!string.IsNullOrWhiteSpace(context.Request.ContentType))
        {
            outgoingRequest.Content.Headers.ContentType = MediaTypeHeaderValue.Parse(context.Request.ContentType);
        }
    }

    foreach (var header in context.Request.Headers)
    {
        if (string.Equals(header.Key, "Host", StringComparison.OrdinalIgnoreCase))
        {
            continue;
        }

        if (!outgoingRequest.Headers.TryAddWithoutValidation(header.Key, header.Value.ToArray()) && outgoingRequest.Content != null)
        {
            outgoingRequest.Content.Headers.TryAddWithoutValidation(header.Key, header.Value.ToArray());
        }
    }

    outgoingRequest.Headers.TryAddWithoutValidation("X-Forwarded-For", context.Connection.RemoteIpAddress?.ToString());
    outgoingRequest.Headers.TryAddWithoutValidation("X-Forwarded-Proto", context.Request.Scheme);
    outgoingRequest.Headers.TryAddWithoutValidation("X-Forwarded-Host", context.Request.Host.Value);

    var client = httpClientFactory.CreateClient("proxy");

    using var upstreamResponse = await client.SendAsync(
        outgoingRequest,
        HttpCompletionOption.ResponseHeadersRead,
        context.RequestAborted);

    context.Response.StatusCode = (int)upstreamResponse.StatusCode;

    foreach (var header in upstreamResponse.Headers)
    {
        context.Response.Headers[header.Key] = header.Value.ToArray();
    }

    foreach (var header in upstreamResponse.Content.Headers)
    {
        context.Response.Headers[header.Key] = header.Value.ToArray();
    }

    context.Response.Headers.Remove("transfer-encoding");

    await using var responseStream = await upstreamResponse.Content.ReadAsStreamAsync(context.RequestAborted);
    await responseStream.CopyToAsync(context.Response.Body, context.RequestAborted);
});

app.MapGet("/", () => Results.Text(
    "Webhook proxy is running. Use /proxy?url=https://allowed-host/path and set ALLOWED_PROXY_HOSTS.",
    "text/plain"));

app.Run();