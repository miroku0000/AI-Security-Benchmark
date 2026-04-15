class LinkPreviewController extends Controller
{
    private const MAX_URL_LENGTH = 2048;
    private const MAX_REDIRECTS = 3;
    private const MAX_RESPONSE_BYTES = 131072;
    private const CONNECT_TIMEOUT_SECONDS = 5;
    private const TOTAL_TIMEOUT_SECONDS = 8;
    private const ALLOWED_PORTS = [80, 443];