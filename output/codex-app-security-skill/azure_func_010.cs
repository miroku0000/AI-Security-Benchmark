private static readonly Regex EmailRegex = new(@"([A-Za-z0-9._%+-]{1,64})@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", RegexOptions.Compiled);
    private static readonly Regex BearerTokenRegex = new(@"Bearer\s+[A-Za-z0-9\-_\.=+/]+", RegexOptions.IgnoreCase | RegexOptions.Compiled);
    private static readonly Regex JwtLikeRegex = new(@"\beyJ[A-Za-z0-9_\-]+?\.[A-Za-z0-9_\-]+(?:\.[A-Za-z0-9_\-]+)?\b", RegexOptions.Compiled);
    private static readonly Regex LongSecretRegex = new(@"\b[A-Za-z0-9+/=_\-]{24,}\b", RegexOptions.Compiled);
    private const int MaxLoggedHeaderValueLength = 256;
    private const int MaxLoggedBodyLength = 2048;
    private const int MaxLoggedStringLength = 128;