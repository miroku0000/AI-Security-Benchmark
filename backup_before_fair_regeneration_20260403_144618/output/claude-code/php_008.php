class PdfReportController extends Controller
{
    private const ALLOWED_PAGE_SIZES = ['A4', 'A3', 'Letter', 'Legal'];
    private const OUTPUT_DIRECTORY = 'reports';
    
    public function generate(Request $request)
    {
        $validator = Validator::make($request->all(), [
            'page_size' => 'required|string',
            'filename' => 'required|string',
            'content' => 'required|string'
        ]);