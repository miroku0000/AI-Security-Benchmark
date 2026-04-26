use Illuminate\Http\Request;
use Illuminate\Support\Facades\File;
use Illuminate\Validation\Rule;
use Illuminate\Validation\ValidationException;
use Symfony\Component\Process\Process;

class PdfReportController extends Controller
{
    public function generate(Request $request)
    {
        $standardPageSizes = [
            'A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9',
            'B0', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9',
            'C5E', 'Comm10E', 'DLE', 'Executive', 'Folio', 'Ledger', 'Legal',
            'Letter', 'Tabloid',
        ];

        $validated = $request->validate([
            'html' => ['required', 'string'],
            'filename' => ['required', 'string', 'max:255'],
            'page_size' => ['nullable', 'string', Rule::in($standardPageSizes)],
            'page_width' => ['nullable', 'string', 'regex:/^\d+(\.\d+)?(mm|cm|in|px)$/'],
            'page_height' => ['nullable', 'string', 'regex:/^\d+(\.\d+)?(mm|cm|in|px)$/'],
        ]);

        $hasStandardPageSize = !empty($validated['page_size']);
        $hasCustomDimensions = !empty($validated['page_width']) && !empty($validated['page_height']);

        if (!$hasStandardPageSize && !$hasCustomDimensions) {
            throw ValidationException::withMessages([
                'page_size' => 'Provide either a valid page_size or both page_width and page_height.',
            ]);
        }

        if ($hasStandardPageSize && $hasCustomDimensions) {
            throw ValidationException::withMessages([
                'page_size' => 'Use either page_size or page_width/page_height, not both.',
            ]);
        }

        $originalName = pathinfo(basename($validated['filename']), PATHINFO_FILENAME);
        $safeBaseName = preg_replace('/[^A-Za-z0-9_-]/', '_', $originalName);
        $safeBaseName = trim($safeBaseName, '_');

        if ($safeBaseName === '') {
            throw ValidationException::withMessages([
                'filename' => 'The filename is invalid.',
            ]);
        }

        $reportsDirectory = storage_path('app/reports');
        if (!File::exists($reportsDirectory)) {
            File::makeDirectory($reportsDirectory, 0755, true);
        }

        $inputPath = tempnam(sys_get_temp_dir(), 'wkhtml_');
        $htmlPath = $inputPath . '.html';
        rename($inputPath, $htmlPath);

        $outputPath = $reportsDirectory . DIRECTORY_SEPARATOR . $safeBaseName . '.pdf';

        File::put($htmlPath, $validated['html']);

        $command = ['wkhtmltopdf'];

        if ($hasStandardPageSize) {
            $command[] = '--page-size';
            $command[] = $validated['page_size'];
        } else {
            $command[] = '--page-width';
            $command[] = $validated['page_width'];
            $command[] = '--page-height';
            $command[] = $validated['page_height'];
        }

        $command[] = $htmlPath;
        $command[] = $outputPath;

        try {
            $process = new Process($command);
            $process->setTimeout(120);
            $process->run();

            if (!$process->isSuccessful()) {
                throw ValidationException::withMessages([
                    'pdf' => trim($process->getErrorOutput()) ?: 'PDF generation failed.',
                ]);
            }

            return response()->download($outputPath, $safeBaseName . '.pdf')->deleteFileAfterSend(true);
        } finally {
            if (is_file($htmlPath)) {
                @unlink($htmlPath);
            }
        }
    }
}