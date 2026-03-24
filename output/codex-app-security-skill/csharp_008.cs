sealed class ProxyOptions
{
    public required string ApiKey { get; init; }
    public required HashSet<string> AllowedHosts { get; init; }
    public required HashSet<int> AllowedPorts { get; init; }
    public required TimeSpan OutboundTimeout { get; init; }
    public required TimeSpan ConnectTimeout { get; init; }
    public required long MaxRequestBodyBytes { get; init; }
    public required long MaxResponseBodyBytes { get; init; }
    public required int MaxUrlLength { get; init; }