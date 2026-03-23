using Microsoft.AspNetCore.Http.Features;

var builder = WebApplication.CreateBuilder(args);
var webRootPath = Path.Combine(builder.Environment.ContentRootPath, "wwwroot");
Directory.CreateDirectory(webRootPath);
builder.WebHost.UseWebRoot(webRootPath);

builder.WebHost.ConfigureKestrel(options =>
{
    options.Limits.MaxRequestBodySize = 50 * 1024 * 1024;
});

builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 50 * 1024 * 1024;
});

var app = builder.Build();

var uploadsDir = Path.Combine(app.Environment.WebRootPath!, "uploads");
Directory.CreateDirectory(uploadsDir);

var imageExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tif", ".tiff", ".ico", ".heic"
};

var imageContentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp", "image/svg+xml",
    "image/tiff", "image/x-icon", "image/heic", "image/heif",
    "application/octet-stream"
};

var documentExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".pdf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".odt", ".ods", ".odp",
    ".txt", ".csv", ".rtf"
};

var documentContentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
    "text/plain", "text/csv", "text/rtf", "application/rtf",
    "application/octet-stream"
};

app.UseStaticFiles();

app.MapPost("/api/upload/avatar", async (HttpRequest request) =>
{
    if (!request.HasFormContentType)
        return Results.BadRequest(new { error = "Expected multipart form data." });

    var form = await request.ReadFormAsync();
    var file = form.Files["file"] ?? form.Files.FirstOrDefault();
    if (file == null || file.Length == 0)
        return Results.BadRequest(new { error = "No file uploaded. Use form field 'file'." });

    return await SaveUploadedFileAsync(file, uploadsDir, imageExtensions, imageContentTypes, subfolder: "avatars");
}).DisableAntiforgery();

app.MapPost("/api/upload/document", async (HttpRequest request) =>
{
    if (!request.HasFormContentType)
        return Results.BadRequest(new { error = "Expected multipart form data." });

    var form = await request.ReadFormAsync();
    var file = form.Files["file"] ?? form.Files.FirstOrDefault();
    if (file == null || file.Length == 0)
        return Results.BadRequest(new { error = "No file uploaded. Use form field 'file'." });

    return await SaveUploadedFileAsync(file, uploadsDir, documentExtensions, documentContentTypes, subfolder: "documents");
}).DisableAntiforgery();

app.MapGet("/", () => Results.Text("POST multipart/form-data to /api/upload/avatar or /api/upload/document with field 'file'."));

app.Run();

static async Task<IResult> SaveUploadedFileAsync(
    IFormFile file,
    string uploadsRoot,
    HashSet<string> allowedExtensions,
    HashSet<string> allowedContentTypes,
    string subfolder)
{
    var ext = Path.GetExtension(file.FileName);
    if (string.IsNullOrEmpty(ext) || !allowedExtensions.Contains(ext))
        return Results.BadRequest(new { error = $"File type not allowed: {ext}" });

    var contentType = file.ContentType;
    if (!string.IsNullOrEmpty(contentType) && !allowedContentTypes.Contains(contentType))
        return Results.BadRequest(new { error = $"Content type not allowed: {contentType}" });

    var safeName = $"{Guid.NewGuid():N}{ext}";
    var targetDir = Path.Combine(uploadsRoot, subfolder);
    Directory.CreateDirectory(targetDir);
    var physicalPath = Path.Combine(targetDir, safeName);

    await using (var stream = File.Create(physicalPath))
    {
        await file.CopyToAsync(stream);
    }

    var relativeWebPath = $"/uploads/{subfolder}/{safeName}".Replace('\\', '/');
    return Results.Ok(new
    {
        path = relativeWebPath,
        fileName = safeName,
        originalFileName = file.FileName,
        size = file.Length,
        contentType = file.ContentType
    });
}
