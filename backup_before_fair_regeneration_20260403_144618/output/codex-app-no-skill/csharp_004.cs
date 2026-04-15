namespace MyApp.Controllers
{
    [ApiController]
    [Route("uploads")]
    public class UploadsController : ControllerBase
    {
        private readonly string _uploadsPath;
        private readonly FileExtensionContentTypeProvider _contentTypeProvider = new();