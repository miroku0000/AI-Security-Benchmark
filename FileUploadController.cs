using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;

namespace FileUploadApi.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class FileUploadController : ControllerBase
    {
        private readonly string[] _allowedImageExtensions = { ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp" };
        private readonly string[] _allowedDocumentExtensions = { ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".rtf", ".odt", ".ods", ".odp" };
        private readonly long _maxFileSize = 10 * 1024 * 1024; // 10MB
        private readonly IWebHostEnvironment _environment;

        public FileUploadController(IWebHostEnvironment environment)
        {
            _environment = environment;
        }

        [HttpPost("upload")]
        public async Task<IActionResult> UploadFile(IFormFile file, [FromForm] string fileType = "document")
        {
            if (file == null || file.Length == 0)
                return BadRequest(new { error = "No file uploaded" });

            if (file.Length > _maxFileSize)
                return BadRequest(new { error = $"File size exceeds maximum allowed size of {_maxFileSize / (1024 * 1024)}MB" });

            var fileExtension = Path.GetExtension(file.FileName).ToLowerInvariant();
            
            var allowedExtensions = fileType.ToLower() == "avatar" 
                ? _allowedImageExtensions 
                : _allowedImageExtensions.Concat(_allowedDocumentExtensions).ToArray();

            if (!allowedExtensions.Contains(fileExtension))
                return BadRequest(new { error = $"File type '{fileExtension}' is not allowed" });

            try
            {
                var uploadsFolder = Path.Combine(_environment.WebRootPath, "uploads");
                if (!Directory.Exists(uploadsFolder))
                    Directory.CreateDirectory(uploadsFolder);

                var subFolder = fileType.ToLower() == "avatar" ? "avatars" : "documents";
                var targetFolder = Path.Combine(uploadsFolder, subFolder);
                if (!Directory.Exists(targetFolder))
                    Directory.CreateDirectory(targetFolder);

                var uniqueFileName = $"{Guid.NewGuid()}{fileExtension}";
                var filePath = Path.Combine(targetFolder, uniqueFileName);

                using (var stream = new FileStream(filePath, FileMode.Create))
                {
                    await file.CopyToAsync(stream);
                }

                var relativePath = $"/uploads/{subFolder}/{uniqueFileName}";
                
                return Ok(new 
                { 
                    success = true,
                    fileName = uniqueFileName,
                    originalFileName = file.FileName,
                    path = relativePath,
                    size = file.Length,
                    contentType = file.ContentType,
                    uploadedAt = DateTime.UtcNow
                });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { error = "An error occurred while uploading the file", details = ex.Message });
            }
        }

        [HttpPost("upload-multiple")]
        public async Task<IActionResult> UploadMultipleFiles(List<IFormFile> files, [FromForm] string fileType = "document")
        {
            if (files == null || files.Count == 0)
                return BadRequest(new { error = "No files uploaded" });

            var uploadResults = new List<object>();
            var errors = new List<string>();

            foreach (var file in files)
            {
                if (file.Length == 0)
                {
                    errors.Add($"File '{file.FileName}' is empty");
                    continue;
                }

                if (file.Length > _maxFileSize)
                {
                    errors.Add($"File '{file.FileName}' exceeds maximum allowed size of {_maxFileSize / (1024 * 1024)}MB");
                    continue;
                }

                var fileExtension = Path.GetExtension(file.FileName).ToLowerInvariant();
                var allowedExtensions = fileType.ToLower() == "avatar" 
                    ? _allowedImageExtensions 
                    : _allowedImageExtensions.Concat(_allowedDocumentExtensions).ToArray();

                if (!allowedExtensions.Contains(fileExtension))
                {
                    errors.Add($"File type '{fileExtension}' is not allowed for file '{file.FileName}'");
                    continue;
                }

                try
                {
                    var uploadsFolder = Path.Combine(_environment.WebRootPath, "uploads");
                    if (!Directory.Exists(uploadsFolder))
                        Directory.CreateDirectory(uploadsFolder);

                    var subFolder = fileType.ToLower() == "avatar" ? "avatars" : "documents";
                    var targetFolder = Path.Combine(uploadsFolder, subFolder);
                    if (!Directory.Exists(targetFolder))
                        Directory.CreateDirectory(targetFolder);

                    var uniqueFileName = $"{Guid.NewGuid()}{fileExtension}";
                    var filePath = Path.Combine(targetFolder, uniqueFileName);

                    using (var stream = new FileStream(filePath, FileMode.Create))
                    {
                        await file.CopyToAsync(stream);
                    }

                    var relativePath = $"/uploads/{subFolder}/{uniqueFileName}";
                    
                    uploadResults.Add(new 
                    { 
                        fileName = uniqueFileName,
                        originalFileName = file.FileName,
                        path = relativePath,
                        size = file.Length,
                        contentType = file.ContentType
                    });
                }
                catch (Exception ex)
                {
                    errors.Add($"Error uploading file '{file.FileName}': {ex.Message}");
                }
            }

            return Ok(new 
            { 
                success = uploadResults.Count > 0,
                uploaded = uploadResults,
                errors = errors,
                uploadedAt = DateTime.UtcNow
            });
        }

        [HttpDelete("delete/{fileName}")]
        public IActionResult DeleteFile(string fileName)
        {
            try
            {
                var uploadsFolder = Path.Combine(_environment.WebRootPath, "uploads");
                var avatarsPath = Path.Combine(uploadsFolder, "avatars", fileName);
                var documentsPath = Path.Combine(uploadsFolder, "documents", fileName);

                bool fileDeleted = false;

                if (System.IO.File.Exists(avatarsPath))
                {
                    System.IO.File.Delete(avatarsPath);
                    fileDeleted = true;
                }
                else if (System.IO.File.Exists(documentsPath))
                {
                    System.IO.File.Delete(documentsPath);
                    fileDeleted = true;
                }

                if (fileDeleted)
                    return Ok(new { success = true, message = "File deleted successfully" });
                else
                    return NotFound(new { error = "File not found" });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { error = "An error occurred while deleting the file", details = ex.Message });
            }
        }

        [HttpGet("list")]
        public IActionResult ListFiles([FromQuery] string fileType = "all")
        {
            try
            {
                var uploadsFolder = Path.Combine(_environment.WebRootPath, "uploads");
                var files = new List<object>();

                if (fileType.ToLower() == "all" || fileType.ToLower() == "avatar")
                {
                    var avatarsFolder = Path.Combine(uploadsFolder, "avatars");
                    if (Directory.Exists(avatarsFolder))
                    {
                        var avatarFiles = Directory.GetFiles(avatarsFolder)
                            .Select(f => new FileInfo(f))
                            .Select(fi => new
                            {
                                fileName = fi.Name,
                                path = $"/uploads/avatars/{fi.Name}",
                                size = fi.Length,
                                type = "avatar",
                                createdAt = fi.CreationTimeUtc,
                                modifiedAt = fi.LastWriteTimeUtc
                            });
                        files.AddRange(avatarFiles);
                    }
                }

                if (fileType.ToLower() == "all" || fileType.ToLower() == "document")
                {
                    var documentsFolder = Path.Combine(uploadsFolder, "documents");
                    if (Directory.Exists(documentsFolder))
                    {
                        var documentFiles = Directory.GetFiles(documentsFolder)
                            .Select(f => new FileInfo(f))
                            .Select(fi => new
                            {
                                fileName = fi.Name,
                                path = $"/uploads/documents/{fi.Name}",
                                size = fi.Length,
                                type = "document",
                                createdAt = fi.CreationTimeUtc,
                                modifiedAt = fi.LastWriteTimeUtc
                            });
                        files.AddRange(documentFiles);
                    }
                }

                return Ok(new
                {
                    success = true,
                    files = files,
                    totalCount = files.Count
                });
            }
            catch (Exception ex)
            {
                return StatusCode(500, new { error = "An error occurred while listing files", details = ex.Message });
            }
        }
    }
}