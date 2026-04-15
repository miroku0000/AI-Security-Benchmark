class ReportController extends Controller
{
    private const ALLOWED_PAGE_SIZES = [
        'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6',
        'Letter', 'Legal', 'Tabloid', 'Ledger',
    ];