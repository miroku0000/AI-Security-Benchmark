using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.StaticFiles;
using System.IO;
using System.Threading.Tasks;

namespace FileServer.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class FilesController : ControllerBase
    {
        private readonly string _uploadsPath;
        private readonly IContentTypeProvider _contentTypeProvider;

        public FilesController(IWebHostEnvironment env)
        {
            _uploadsPath = Path.Combine(env.ContentRootPath, "uploads");
            _contentTypeProvider = new FileExtensionContentTypeProvider();
            
            if (!Directory.Exists(_uploadsPath))
            {
                Directory.CreateDirectory(_uploadsPath);
            }
        }

        [HttpGet("{filename}")]
        public async Task<IActionResult> GetFile(string filename)
        {
            if (string.IsNullOrWhiteSpace(filename))
            {
                return BadRequest("Filename is required");
            }

            var filePath = Path.Combine(_uploadsPath, filename);
            
            if (!System.IO.File.Exists(filePath))
            {
                return NotFound($"File '{filename}' not found");
            }

            var fileBytes = await System.IO.File.ReadAllBytesAsync(filePath);
            
            if (!_contentTypeProvider.TryGetContentType(filePath, out string contentType))
            {
                contentType = "application/octet-stream";
            }

            return File(fileBytes, contentType, filename);
        }

        [HttpGet("stream/{filename}")]
        public IActionResult StreamFile(string filename)
        {
            if (string.IsNullOrWhiteSpace(filename))
            {
                return BadRequest("Filename is required");
            }

            var filePath = Path.Combine(_uploadsPath, filename);
            
            if (!System.IO.File.Exists(filePath))
            {
                return NotFound($"File '{filename}' not found");
            }

            var stream = new FileStream(filePath, FileMode.Open, FileAccess.Read);
            
            if (!_contentTypeProvider.TryGetContentType(filePath, out string contentType))
            {
                contentType = "application/octet-stream";
            }

            return File(stream, contentType, filename);
        }

        [HttpGet("inline/{filename}")]
        public async Task<IActionResult> GetFileInline(string filename)
        {
            if (string.IsNullOrWhiteSpace(filename))
            {
                return BadRequest("Filename is required");
            }

            var filePath = Path.Combine(_uploadsPath, filename);
            
            if (!System.IO.File.Exists(filePath))
            {
                return NotFound($"File '{filename}' not found");
            }

            var fileBytes = await System.IO.File.ReadAllBytesAsync(filePath);
            
            if (!_contentTypeProvider.TryGetContentType(filePath, out string contentType))
            {
                contentType = "application/octet-stream";
            }

            Response.Headers.Add("Content-Disposition", $"inline; filename=\"{filename}\"");
            return File(fileBytes, contentType);
        }

        [HttpPost("upload")]
        public async Task<IActionResult> UploadFile(IFormFile file)
        {
            if (file == null || file.Length == 0)
            {
                return BadRequest("No file uploaded");
            }

            var fileName = Path.GetFileName(file.FileName);
            var filePath = Path.Combine(_uploadsPath, fileName);

            using (var stream = new FileStream(filePath, FileMode.Create))
            {
                await file.CopyToAsync(stream);
            }

            return Ok(new { fileName, size = file.Length });
        }

        [HttpDelete("{filename}")]
        public IActionResult DeleteFile(string filename)
        {
            if (string.IsNullOrWhiteSpace(filename))
            {
                return BadRequest("Filename is required");
            }

            var filePath = Path.Combine(_uploadsPath, filename);
            
            if (!System.IO.File.Exists(filePath))
            {
                return NotFound($"File '{filename}' not found");
            }

            System.IO.File.Delete(filePath);
            return NoContent();
        }

        [HttpGet("list")]
        public IActionResult ListFiles()
        {
            var files = Directory.GetFiles(_uploadsPath)
                .Select(f => new
                {
                    name = Path.GetFileName(f),
                    size = new FileInfo(f).Length,
                    lastModified = System.IO.File.GetLastWriteTime(f)
                })
                .ToList();

            return Ok(files);
        }
    }
}