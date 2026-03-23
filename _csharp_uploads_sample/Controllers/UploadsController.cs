using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.StaticFiles;

namespace FileUploadApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UploadsController : ControllerBase
{
    private readonly IWebHostEnvironment _env;
    private readonly IContentTypeProvider _contentTypeProvider;

    public UploadsController(IWebHostEnvironment env, IContentTypeProvider contentTypeProvider)
    {
        _env = env;
        _contentTypeProvider = contentTypeProvider;
    }

    [HttpGet("{fileName}")]
    public IActionResult Get(string fileName)
    {
        if (string.IsNullOrWhiteSpace(fileName))
            return BadRequest();

        fileName = Path.GetFileName(fileName);
        if (string.IsNullOrEmpty(fileName))
            return BadRequest();

        var uploadsRoot = Path.GetFullPath(Path.Combine(_env.ContentRootPath, "uploads"));
        var physicalPath = Path.GetFullPath(Path.Combine(uploadsRoot, fileName));

        if (!IsUnderDirectory(physicalPath, uploadsRoot))
            return BadRequest();

        if (!System.IO.File.Exists(physicalPath))
            return NotFound();

        if (!_contentTypeProvider.TryGetContentType(fileName, out var contentType))
            contentType = "application/octet-stream";

        return PhysicalFile(physicalPath, contentType, enableRangeProcessing: true);
    }

    private static bool IsUnderDirectory(string candidate, string directory)
    {
        var dir = Path.TrimEndingDirectorySeparator(Path.GetFullPath(directory));
        var path = Path.GetFullPath(candidate);
        return path.StartsWith(dir + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
            || string.Equals(path, dir, StringComparison.OrdinalIgnoreCase);
    }
}
