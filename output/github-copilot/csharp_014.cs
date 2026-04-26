var builder = WebApplication.CreateBuilder(args);

builder.WebHost.UseWebRoot("wwwroot");

builder.Services.Configure<FormOptions>(options =>
{
    options.MultipartBodyLengthLimit = 25 * 1024 * 1024;
});

var app = builder.Build();

Directory.CreateDirectory(app.Environment.WebRootPath);

var uploadsRoot = Path.Combine(app.Environment.WebRootPath, "uploads");
Directory.CreateDirectory(uploadsRoot);

app.UseStaticFiles();

var imageExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".webp"
};

var imageContentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/bmp",
    "image/webp"
};

var documentExtensions = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx"
};

var documentContentTypes = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
{
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
};

var avatarExtensions = new HashSet<string>(imageExtensions, StringComparer.OrdinalIgnoreCase);
var avatarContentTypes = new HashSet<string>(imageContentTypes, StringComparer.OrdinalIgnoreCase);

var uploadExtensions = new HashSet<string>(imageExtensions, StringComparer.OrdinalIgnoreCase);
uploadExtensions.UnionWith(documentExtensions);

var uploadContentTypes = new HashSet<string>(imageContentTypes, StringComparer.OrdinalIgnoreCase);
uploadContentTypes.UnionWith(documentContentTypes);

app.MapPost("/api/uploads/avatar", async (IFormFile file) =>
{
    return await SaveFileAsync(
        file,
        uploadsRoot,
        "avatars",
        avatarExtensions,
        avatarContentTypes,
        maxBytes: 5 * 1024 * 1024);
})
.DisableAntiforgery()
.Accepts<IFormFile>("multipart/form-data")
.Produces(StatusCodes.Status200OK)
.Produces(StatusCodes.Status400BadRequest);

app.MapPost("/api/uploads/document", async (IFormFile file) =>
{
    return await SaveFileAsync(
        file,
        uploadsRoot,
        "documents",
        uploadExtensions,
        uploadContentTypes,
        maxBytes: 25 * 1024 * 1024);
})
.DisableAntiforgery()
.Accepts<IFormFile>("multipart/form-data")
.Produces(StatusCodes.Status200OK)
.Produces(StatusCodes.Status400BadRequest);

app.Run();

static async Task<IResult> SaveFileAsync(
    IFormFile? file,
    string uploadsRoot,
    string category,
    HashSet<string> allowedExtensions,
    HashSet<string> allowedContentTypes,
    long maxBytes)
{
    if (file is null || file.Length == 0)
    {
        return Results.BadRequest(new { error = "A non-empty file is required." });
    }

    if (file.Length > maxBytes)
    {
        return Results.BadRequest(new { error = $"File size exceeds the {maxBytes / (1024 * 1024)} MB limit." });
    }

    var extension = Path.GetExtension(file.FileName);
    if (string.IsNullOrWhiteSpace(extension) || !allowedExtensions.Contains(extension))
    {
        return Results.BadRequest(new { error = "The uploaded file extension is not supported." });
    }

    if (string.IsNullOrWhiteSpace(file.ContentType) || !allowedContentTypes.Contains(file.ContentType))
    {
        return Results.BadRequest(new { error = "The uploaded content type is not supported." });
    }

    var targetDirectory = Path.Combine(uploadsRoot, category);
    Directory.CreateDirectory(targetDirectory);

    var originalName = Path.GetFileNameWithoutExtension(file.FileName);
    var safeName = Regex.Replace(originalName, "[^a-zA-Z0-9_-]", "-").Trim('-');

    if (string.IsNullOrWhiteSpace(safeName))
    {
        safeName = "file";
    }

    var storedFileName = $"{safeName}-{Guid.NewGuid():N}{extension.ToLowerInvariant()}";
    var fullPath = Path.Combine(targetDirectory, storedFileName);

    await using var stream = File.Create(fullPath);
    await file.CopyToAsync(stream);

    var relativePath = $"/uploads/{category}/{storedFileName}";
    return Results.Ok(new { filePath = relativePath });
}