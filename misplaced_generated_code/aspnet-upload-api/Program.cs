using System.Globalization;
using System.Security.Cryptography;
using Microsoft.AspNetCore.Http.Features;

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<FormOptions>(o =>
{
    o.MultipartBodyLengthLimit = 30L * 1024L * 1024L;
});

var app = builder.Build();

app.UseHttpsRedirection();
app.UseStaticFiles();

var webRoot = app.Environment.WebRootPath;
if (string.IsNullOrWhiteSpace(webRoot))
{
    webRoot = Path.Combine(app.Environment.ContentRootPath, "wwwroot");
}

var uploadsRoot = Path.Combine(webRoot, "uploads");
var avatarsRoot = Path.Combine(uploadsRoot, "avatars");
var documentsRoot = Path.Combine(uploadsRoot, "documents");
Directory.CreateDirectory(avatarsRoot);
Directory.CreateDirectory(documentsRoot);

var imageExts = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".jpg", ".jpeg", ".png", ".gif", ".webp" };
var docExts = new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx" };

app.MapPost("/upload/avatar", async (HttpRequest request, IFormFile file, CancellationToken ct) =>
{
    const long maxBytes = 5L * 1024L * 1024L;
    if (file.Length <= 0 || file.Length > maxBytes) return Results.BadRequest(new { error = "Invalid file size." });

    var ext = NormalizeExt(file.FileName);
    if (!imageExts.Contains(ext)) return Results.BadRequest(new { error = "Unsupported file type." });

    var relativePath = await SaveUploadAsync(file, avatarsRoot, "/uploads/avatars", ext, ct);
    return Results.Ok(new { path = relativePath });
})
.DisableAntiforgery()
.Accepts<IFormFile>("multipart/form-data")
.Produces(StatusCodes.Status200OK)
.Produces(StatusCodes.Status400BadRequest);

app.MapPost("/upload/document", async (HttpRequest request, IFormFile file, CancellationToken ct) =>
{
    const long maxBytes = 25L * 1024L * 1024L;
    if (file.Length <= 0 || file.Length > maxBytes) return Results.BadRequest(new { error = "Invalid file size." });

    var ext = NormalizeExt(file.FileName);
    if (!(docExts.Contains(ext) || imageExts.Contains(ext))) return Results.BadRequest(new { error = "Unsupported file type." });

    var relativePath = await SaveUploadAsync(file, documentsRoot, "/uploads/documents", ext, ct);
    return Results.Ok(new { path = relativePath });
})
.DisableAntiforgery()
.Accepts<IFormFile>("multipart/form-data")
.Produces(StatusCodes.Status200OK)
.Produces(StatusCodes.Status400BadRequest);

app.Run();

static string NormalizeExt(string fileName)
{
    var ext = Path.GetExtension(fileName ?? string.Empty);
    if (string.IsNullOrWhiteSpace(ext)) return string.Empty;
    if (ext.Length > 10) return string.Empty;
    return ext.ToLowerInvariant();
}

static async Task<string> SaveUploadAsync(IFormFile file, string physicalDir, string publicBasePath, string ext, CancellationToken ct)
{
    var safeExt = string.IsNullOrWhiteSpace(ext) ? ".bin" : ext;
    var now = DateTimeOffset.UtcNow;
    var y = now.Year.ToString("0000", CultureInfo.InvariantCulture);
    var m = now.Month.ToString("00", CultureInfo.InvariantCulture);
    var d = now.Day.ToString("00", CultureInfo.InvariantCulture);

    var datedDir = Path.Combine(physicalDir, y, m, d);
    Directory.CreateDirectory(datedDir);

    var randomName = $"{now:yyyyMMddHHmmss}-{ToHex(RandomNumberGenerator.GetBytes(12))}{safeExt}";
    var physicalPath = Path.Combine(datedDir, randomName);

    await using (var stream = new FileStream(physicalPath, FileMode.CreateNew, FileAccess.Write, FileShare.None, 64 * 1024, FileOptions.Asynchronous))
    {
        await file.CopyToAsync(stream, ct);
    }

    var relative = $"{publicBasePath}/{y}/{m}/{d}/{randomName}";
    return relative;
}

static string ToHex(ReadOnlySpan<byte> bytes)
{
    return Convert.ToHexString(bytes).ToLowerInvariant();
}

