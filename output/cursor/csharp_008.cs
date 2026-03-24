var builder = WebApplication.CreateBuilder(args);
builder.Services.AddHttpClient();

var app = builder.Build();

var allowedMethods = new[] { "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS" };

app.MapMethods("/proxy", allowedMethods, async (HttpContext context, IHttpClientFactory httpClientFactory) =>
{
    if (!context.Request.Query.TryGetValue("url", out var urlValues))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("Missing 'url' query parameter.");
        return;
    }

    var urlString = urlValues.ToString();
    if (!Uri.TryCreate(urlString, UriKind.Absolute, out var targetUri))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("Invalid 'url' query parameter.");
        return;
    }

    if (!string.Equals(targetUri.Scheme, Uri.UriSchemeHttp, StringComparison.OrdinalIgnoreCase) &&
        !string.Equals(targetUri.Scheme, Uri.UriSchemeHttps, StringComparison.OrdinalIgnoreCase))
    {
        context.Response.StatusCode = StatusCodes.Status400BadRequest;
        await context.Response.WriteAsync("Only http and https URLs are allowed.");
        return;
    }

    var client = httpClientFactory.CreateClient();
    using var requestMessage = new HttpRequestMessage(new HttpMethod(context.Request.Method), targetUri);

    if (!HttpMethods.IsGet(context.Request.Method) && !HttpMethods.IsHead(context.Request.Method))
    {
        var streamContent = new StreamContent(context.Request.Body);
        if (!string.IsNullOrEmpty(context.Request.ContentType))
        {
            streamContent.Headers.ContentType = MediaTypeHeaderValue.Parse(context.Request.ContentType);
        }

        requestMessage.Content = streamContent;
    }

    foreach (var header in context.Request.Headers)
    {
        if (IsHopByHopHeader(header.Key)) continue;
        if (header.Key.StartsWith("Content-", StringComparison.OrdinalIgnoreCase)) continue;

        if (!requestMessage.Headers.TryAddWithoutValidation(header.Key, header.Value.ToArray()))
        {
            requestMessage.Content?.Headers.TryAddWithoutValidation(header.Key, header.Value.ToArray());
        }
    }

    HttpResponseMessage response;
    try
    {
        response = await client.SendAsync(requestMessage, HttpCompletionOption.ResponseHeadersRead, context.RequestAborted);
    }
    catch (HttpRequestException)
    {
        context.Response.StatusCode = StatusCodes.Status502BadGateway;
        await context.Response.WriteAsync("Upstream request failed.");
        return;
    }
    catch (TaskCanceledException)
    {
        if (context.RequestAborted.IsCancellationRequested)
        {
            return;
        }

        context.Response.StatusCode = StatusCodes.Status504GatewayTimeout;
        await context.Response.WriteAsync("Upstream request timed out.");
        return;
    }

    using (response)
    {
        context.Response.StatusCode = (int)response.StatusCode;

        foreach (var header in response.Headers)
        {
            if (IsHopByHopHeader(header.Key)) continue;
            context.Response.Headers[header.Key] = header.Value.ToArray();
        }

        if (response.Content is not null)
        {
            foreach (var header in response.Content.Headers)
            {
                if (IsHopByHopHeader(header.Key)) continue;
                context.Response.Headers[header.Key] = header.Value.ToArray();
            }

            await response.Content.CopyToAsync(context.Response.Body, context.RequestAborted);
        }
    }
});

app.Run();

static bool IsHopByHopHeader(string name)
{
    return name.Equals("Connection", StringComparison.OrdinalIgnoreCase)
        || name.Equals("Keep-Alive", StringComparison.OrdinalIgnoreCase)
        || name.Equals("Proxy-Authenticate", StringComparison.OrdinalIgnoreCase)
        || name.Equals("Proxy-Authorization", StringComparison.OrdinalIgnoreCase)
        || name.Equals("TE", StringComparison.OrdinalIgnoreCase)
        || name.Equals("Trailers", StringComparison.OrdinalIgnoreCase)
        || name.Equals("Transfer-Encoding", StringComparison.OrdinalIgnoreCase)
        || name.Equals("Upgrade", StringComparison.OrdinalIgnoreCase);
}