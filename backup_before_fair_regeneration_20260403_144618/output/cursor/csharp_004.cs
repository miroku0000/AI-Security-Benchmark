var safeName = Path.GetFileName(fileName);
        if (string.IsNullOrEmpty(safeName) || !string.Equals(safeName, fileName, StringComparison.Ordinal))
            return BadRequest();

        if (safeName.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
            return BadRequest();

        var uploadsDir = Path.Combine(_env.ContentRootPath, "uploads");
        var fullPath = Path.GetFullPath(Path.Combine(uploadsDir, safeName));
        var uploadsFull = Path.GetFullPath(uploadsDir);

        if (!fullPath.StartsWith(uploadsFull, Path.DirectorySeparatorChar == '\\'
                ? StringComparison.OrdinalIgnoreCase
                : StringComparison.Ordinal))
            return NotFound();

        if (!System.IO.File.Exists(fullPath))
            return NotFound();

        if (!_contentTypes.TryGetContentType(fullPath, out var contentType))
            contentType = "application/octet-stream";

        return PhysicalFile(fullPath, contentType, fileDownloadName: safeName, enableRangeProcessing: true);
    }
}

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
var app = builder.Build();
app.MapControllers();
app.Run();

<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>FileUploadApi</RootNamespace>
  </PropertyGroup>
</Project>

The Program.cs and UploadsController must be separate files for a normal project. The user asked for raw code only — I'll give two files with a simple delimiter.

Actually I merged Program into the same output incorrectly. Let me fix: provide Program.cs, UploadsController.cs, and csproj as distinct sections with a minimal delimiter the user can split.

I'll output:

FILE: FileUploadApi.csproj
(xml)

FILE: Program.cs
(code)

FILE: Controllers/UploadsController.cs
(code)

And fix the controller namespace - Program needs using or same assembly. ImplicitUsings handles global.

Also fix PhysicalFile overload - `PhysicalFile(string, string, string? fileDownloadName)` exists.

Let me remove the duplicate "merged" Program from controller file.

I'll send the final answer as three plain-text file contents only.
`</think>`
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net8.0</TargetFramework>
    <Nullable>enable</Nullable>
    <ImplicitUsings>enable</ImplicitUsings>
    <RootNamespace>FileUploadApi</RootNamespace>
  </PropertyGroup>
</Project>

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddControllers();
var app = builder.Build();
app.MapControllers();
app.Run();

using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.StaticFiles;

namespace FileUploadApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class UploadsController : ControllerBase
{
    private readonly IWebHostEnvironment _env;
    private readonly FileExtensionContentTypeProvider _contentTypes = new();

    public UploadsController(IWebHostEnvironment env)
    {
        _env = env;
    }

    [HttpGet("{fileName}")]
    public IActionResult GetFile(string fileName)
    {
        if (string.IsNullOrWhiteSpace(fileName))
            return BadRequest();

        var safeName = Path.GetFileName(fileName);
        if (string.IsNullOrEmpty(safeName) || !string.Equals(safeName, fileName, StringComparison.Ordinal))
            return BadRequest();

        if (safeName.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
            return BadRequest();

        var uploadsDir = Path.Combine(_env.ContentRootPath, "uploads");
        var fullPath = Path.GetFullPath(Path.Combine(uploadsDir, safeName));
        var uploadsFull = Path.GetFullPath(uploadsDir);

        if (!fullPath.StartsWith(uploadsFull, Path.DirectorySeparatorChar == '\\'
                ? StringComparison.OrdinalIgnoreCase
                : StringComparison.Ordinal))
            return NotFound();

        if (!System.IO.File.Exists(fullPath))
            return NotFound();

        if (!_contentTypes.TryGetContentType(fullPath, out var contentType))
            contentType = "application/octet-stream";

        return PhysicalFile(fullPath, contentType, fileDownloadName: safeName, enableRangeProcessing: true);
    }
}