using System;
using System.IdentityModel.Tokens.Jwt;
using System.Linq;
using System.Security.Claims;
using System.Text;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Configuration;
using Microsoft.IdentityModel.Tokens;

public class JwtAuthenticationMiddleware
{
    private readonly RequestDelegate _next;
    private readonly IConfiguration _configuration;
    private readonly JwtSecurityTokenHandler _tokenHandler;

    public JwtAuthenticationMiddleware(RequestDelegate next, IConfiguration configuration)
    {
        _next = next;
        _configuration = configuration;
        _tokenHandler = new JwtSecurityTokenHandler();
    }

    public async Task InvokeAsync(HttpContext context)
    {
        var token = ExtractTokenFromHeader(context);

        if (!string.IsNullOrEmpty(token))
        {
            await ValidateAndSetUser(context, token);
        }

        await _next(context);
    }

    private string ExtractTokenFromHeader(HttpContext context)
    {
        string authorizationHeader = context.Request.Headers["Authorization"].FirstOrDefault();

        if (string.IsNullOrEmpty(authorizationHeader))
        {
            return null;
        }

        if (authorizationHeader.StartsWith("Bearer ", StringComparison.OrdinalIgnoreCase))
        {
            return authorizationHeader.Substring("Bearer ".Length).Trim();
        }

        return null;
    }

    private async Task ValidateAndSetUser(HttpContext context, string token)
    {
        try
        {
            var validationParameters = new TokenValidationParameters
            {
                ValidateIssuer = true,
                ValidateAudience = true,
                ValidateLifetime = true,
                ValidateIssuerSigningKey = true,
                ValidIssuer = _configuration["Jwt:Issuer"],
                ValidAudience = _configuration["Jwt:Audience"],
                IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_configuration["Jwt:SecretKey"])),
                ClockSkew = TimeSpan.Zero
            };

            ClaimsPrincipal principal = _tokenHandler.ValidateToken(token, validationParameters, out SecurityToken validatedToken);

            var jwtToken = (JwtSecurityToken)validatedToken;

            if (jwtToken == null)
            {
                return;
            }

            var identity = new ClaimsIdentity(principal.Claims, "Jwt");
            
            context.User = new ClaimsPrincipal(identity);
            context.Items["JwtToken"] = token;
            context.Items["TokenValidated"] = true;
        }
        catch (SecurityTokenValidationException)
        {
            context.Items["TokenValidated"] = false;
        }
        catch (Exception)
        {
            context.Items["TokenValidated"] = false;
        }
    }
}

public static class JwtAuthenticationMiddlewareExtensions
{
    public static IApplicationBuilder UseJwtAuthentication(this IApplicationBuilder builder)
    {
        return builder.UseMiddleware<JwtAuthenticationMiddleware>();
    }
}