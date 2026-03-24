sealed class JwtAuthenticationMiddleware
{
    private const int MaxAuthorizationHeaderLength = 8192;
    private const string BearerPrefix = "Bearer ";
    private readonly RequestDelegate _next;
    private readonly JwtAuthOptions _options;