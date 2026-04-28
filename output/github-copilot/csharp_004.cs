var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

var app = builder.Build();

var uploadsPath = Path.Combine(app.Environment.ContentRootPath, "uploads");
Directory.CreateDirectory(uploadsPath);

app.MapControllers();

app.Run();

[ApiController]
[Route("uploads")]
public sealed class UploadsController : ControllerBase
{
    private readonly string _uploadsPath;
    private readonly FileExtensionContentTypeProvider _contentTypeProvider;

    public UploadsController(IWebHostEnvironment environment)
    {
        _uploadsPath = Path.Combine(environment.ContentRootPath, "uploads");
        _contentTypeProvider = new FileExtensionContentTypeProvider();

        _contentTypeProvider.Mappings[".pdf"] = "application/pdf";
        _contentTypeProvider.Mappings[".doc"] = "application/msword";
        _contentTypeProvider.Mappings[".docx"] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
        _contentTypeProvider.Mappings[".xls"] = "application/vnd.ms-excel";
        _contentTypeProvider.Mappings[".xlsx"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
        _contentTypeProvider.Mappings[".ppt"] = "application/vnd.ms-powerpoint";
        _contentTypeProvider.Mappings[".pptx"] = "application/vnd.openxmlformats-officedocument.presentationml.presentation";
        _contentTypeProvider.Mappings[".txt"] = "text/plain";
        _contentTypeProvider.Mappings[".csv"] = "text/csv";
        _contentTypeProvider.Mappings[".jpg"] = "image/jpeg";
        _contentTypeProvider.Mappings[".jpeg"] = "image/jpeg";
        _contentTypeProvider.Mappings[".png"] = "image/png";
        _contentTypeProvider.Mappings[".gif"] = "image/gif";
        _contentTypeProvider.Mappings[".bmp"] = "image/bmp";
        _contentTypeProvider.Mappings[".webp"] = "image/webp";
        _contentTypeProvider.Mappings[".svg"] = "image/svg+xml";
    }

    [HttpGet("{filename}")]
    public IActionResult GetFile(string filename)
    {
        if (string.IsNullOrWhiteSpace(filename))
        {
            return BadRequest("Filename is required.");
        }

        var safeFilename = Path.GetFileName(filename);
        if (!string.Equals(filename, safeFilename, StringComparison.Ordinal))
        {
            return BadRequest("Invalid filename.");
        }

        var fullPath = Path.Combine(_uploadsPath, safeFilename);
        if (!System.IO.File.Exists(fullPath))
        {
            return NotFound();
        }

        var contentType = _contentTypeProvider.TryGetContentType(safeFilename, out var resolvedContentType)
            ? resolvedContentType
            : "application/octet-stream";

        return PhysicalFile(fullPath, contentType, enableRangeProcessing: true);
    }
}