public sealed class JwtAuthenticationOptions
{
    public string IssuerSigningKey { get; set; } = string.Empty;
    public string? ValidIssuer { get; set; }
    public string? ValidAudience { get; set; }
    public bool ValidateIssuer { get; set; }
    public bool ValidateAudience { get; set; }
    public bool ValidateLifetime { get; set; } = true;
    public bool RequireHttpsMetadata { get; set; } = true;
    public TimeSpan ClockSkew { get; set; } = TimeSpan.FromMinutes(5);
}