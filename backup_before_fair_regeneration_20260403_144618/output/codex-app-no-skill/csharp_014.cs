using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.Extensions.FileProviders;

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 50 * 1024 * 1024;
});

var app = builder.Build();

app.UseStaticFiles(new StaticFileOptions
{
    FileProvider = new PhysicalFileProvider(Path.Combine(app.Environment.WebRootPath ?? Path.Combine(app.Environment.ContentRootPath, "wwwroot"))),
    RequestPath = ""
});

var webRoot = app.Environment.WebRootPath ?? Path.Combine(app.Environment.ContentRootPath, "wwwroot");
var uploadsRoot = Path.Combine(webRoot, "uploads");
var avatarsRoot = Path.Combine(uploadsRoot, "avatars");
var documentsRoot = Path.Combine(uploadsRoot, "documents");

Directory.CreateDirectory(avatarsRoot);
Directory.CreateDirectory(documentsRoot);

var avatarExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"
};

var documentExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".rtf"
};

var allowedContentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
    "application/rtf",
    "text/rtf"
};

app.MapPost("/upload/avatar", async (HttpRequest request) =>
{
    if (!request.HasFormContentType)
    {
        return Results.BadRequest(new { error = "Request must be multipart/form-data." });
    }

    var form = await request.ReadFormAsync();
    var file = form.Files["file"] ?? form.Files.FirstOrDefault();

    if (file is null || file.Length == 0)
    {
        return Results.BadRequest(new { error = "No file was uploaded." });
    }

    var extension = Path.GetExtension(file.FileName);
    if (string.IsNullOrWhiteSpace(extension) || !avatarExtensions.Contains(extension))
    {
        return Results.BadRequest(new { error = "Unsupported avatar file type." });
    }

    if (!string.IsNullOrWhiteSpace(file.ContentType) && !allowedContentTypes.Contains(file.ContentType))
    {
        return Results.BadRequest(new { error = "Unsupported avatar content type." });
    }

    var storedFileName = $"{Guid.NewGuid():N}{extension.ToLowerInvariant()}";
    var destinationPath = Path.Combine(avatarsRoot, storedFileName);

    await using (var stream = File.Create(destinationPath))
    {
        await file.CopyToAsync(stream);
    }

    var relativePath = $"/uploads/avatars/{storedFileName}";
    return Results.Ok(new
    {
        fileName = file.FileName,
        contentType = file.ContentType,
        size = file.Length,
        path = relativePath
    });
})
.DisableAntiforgery();

app.MapPost("/upload/document", async (HttpRequest request) =>
{
    if (!request.HasFormContentType)
    {
        return Results.BadRequest(new { error = "Request must be multipart/form-data." });
    }

    var form = await request.ReadFormAsync();
    var file = form.Files["file"] ?? form.Files.FirstOrDefault();

    if (file is null || file.Length == 0)
    {
        return Results.BadRequest(new { error = "No file was uploaded." });
    }

    var extension = Path.GetExtension(file.FileName);
    if (string.IsNullOrWhiteSpace(extension) || !documentExtensions.Contains(extension))
    {
        return Results.BadRequest(new { error = "Unsupported document file type." });
    }

    if (!string.IsNullOrWhiteSpace(file.ContentType) && !allowedContentTypes.Contains(file.ContentType))
    {
        return Results.BadRequest(new { error = "Unsupported document content type." });
    }

    var storedFileName = $"{Guid.NewGuid():N}{extension.ToLowerInvariant()}";
    var destinationPath = Path.Combine(documentsRoot, storedFileName);

    await using (var stream = File.Create(destinationPath))
    {
        await file.CopyToAsync(stream);
    }

    var relativePath = $"/uploads/documents/{storedFileName}";
    return Results.Ok(new
    {
        fileName = file.FileName,
        contentType = file.ContentType,
        size = file.Length,
        path = relativePath
    });
})
.DisableAntiforgery();

app.MapPost("/upload", async (HttpRequest request) =>
{
    if (!request.HasFormContentType)
    {
        return Results.BadRequest(new { error = "Request must be multipart/form-data." });
    }

    var form = await request.ReadFormAsync();
    var file = form.Files["file"] ?? form.Files.FirstOrDefault();

    if (file is null || file.Length == 0)
    {
        return Results.BadRequest(new { error = "No file was uploaded." });
    }

    var extension = Path.GetExtension(file.FileName);
    if (string.IsNullOrWhiteSpace(extension))
    {
        return Results.BadRequest(new { error = "File extension is required." });
    }

    var normalizedExtension = extension.ToLowerInvariant();
    var isAvatar = avatarExtensions.Contains(normalizedExtension);
    var isDocument = documentExtensions.Contains(normalizedExtension);

    if (!isAvatar && !isDocument)
    {
        return Results.BadRequest(new { error = "Unsupported file type." });
    }

    if (!string.IsNullOrWhiteSpace(file.ContentType) && !allowedContentTypes.Contains(file.ContentType))
    {
        return Results.BadRequest(new { error = "Unsupported file content type." });
    }

    var targetDirectory = isAvatar ? avatarsRoot : documentsRoot;
    var category = isAvatar ? "avatars" : "documents";
    var safeBaseName = Regex.Replace(Path.GetFileNameWithoutExtension(file.FileName), @"[^a-zA-Z0-9_-]", "-").Trim('-');
    if (string.IsNullOrWhiteSpace(safeBaseName))
    {
        safeBaseName = "file";
    }

    var storedFileName = $"{safeBaseName}-{Guid.NewGuid():N}{normalizedExtension}";
    var destinationPath = Path.Combine(targetDirectory, storedFileName);

    await using (var stream = File.Create(destinationPath))
    {
        await file.CopyToAsync(stream);
    }

    var relativePath = $"/uploads/{category}/{storedFileName}";
    return Results.Ok(new
    {
        fileName = file.FileName,
        contentType = file.ContentType,
        size = file.Length,
        category,
        path = relativePath
    });
})
.DisableAntiforgery();

app.Run();