using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.StaticFiles;

namespace FileServerApp.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UploadsController : ControllerBase
{
    private readonly IWebHostEnvironment _env;
    private static readonly FileExtensionContentTypeProvider ContentTypes = new();

    public UploadsController(IWebHostEnvironment env)
    {
        _env = env;
    }

    [HttpGet("{filename}")]
    public IActionResult Get(string filename)
    {
        if (string.IsNullOrWhiteSpace(filename))
            return BadRequest();

        if (filename.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 || filename.Contains("..", StringComparison.Ordinal))
            return BadRequest();

        var uploadsRoot = Path.GetFullPath(Path.Combine(_env.ContentRootPath, "uploads"));
        var filePath = Path.GetFullPath(Path.Combine(uploadsRoot, filename));

        var relative = Path.GetRelativePath(uploadsRoot, filePath);
        if (relative.StartsWith("..", StringComparison.Ordinal) || Path.IsPathRooted(relative))
            return BadRequest();

        if (!System.IO.File.Exists(filePath))
            return NotFound();

        if (!ContentTypes.TryGetContentType(filename, out var contentType) || string.IsNullOrEmpty(contentType))
            contentType = "application/octet-stream";

        return PhysicalFile(filePath, contentType, enableRangeProcessing: true);
    }
}
