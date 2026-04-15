<?php

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\BinaryFileResponse;

class PdfReportController extends Controller
{
    public function generate(Request $request): BinaryFileResponse|JsonResponse
    {
        $validated = $request->validate([
            'page_size' => ['required', 'string', 'max:64'],
            'filename' => ['required', 'string', 'max:255'],
            'html' => ['required', 'string'],
            'parameters' => ['sometimes', 'array'],
            'parameters.*' => ['string', 'max:256'],
        ]);

        $pageSize = trim($validated['page_size']);
        $filename = basename($validated['filename']);
        if ($filename === '' || $filename === '.' || $filename === '..') {
            return response()->json(['message' => 'Invalid filename.'], 422);
        }
        if (! str_ends_with(strtolower($filename), '.pdf')) {
            $filename .= '.pdf';
        }

        $htmlPath = tempnam(sys_get_temp_dir(), 'wkhtml_');
        if ($htmlPath === false) {
            return response()->json(['message' => 'Could not create temporary file.'], 500);
        }
        rename($htmlPath, $htmlPath . '.html');
        $htmlPath .= '.html';

        file_put_contents($htmlPath, $validated['html']);

        $reportsDir = storage_path('app/reports');
        if (! is_dir($reportsDir) && ! mkdir($reportsDir, 0755, true) && ! is_dir($reportsDir)) {
            @unlink($htmlPath);
            return response()->json(['message' => 'Could not create output directory.'], 500);
        }

        $outputPath = $reportsDir . DIRECTORY_SEPARATOR . $filename;

        $parts = ['wkhtmltopdf'];
        $parts[] = '--page-size';
        $parts[] = $pageSize;
        if (! empty($validated['parameters']) && is_array($validated['parameters'])) {
            foreach ($validated['parameters'] as $p) {
                $parts[] = $p;
            }
        }
        $parts[] = $htmlPath;
        $parts[] = $outputPath;

        $escaped = array_map(static fn (string $s): string => escapeshellarg($s), $parts);
        $command = implode(' ', $escaped);

        $output = [];
        $exitCode = 0;
        exec($command . ' 2>&1', $output, $exitCode);

        @unlink($htmlPath);

        if ($exitCode !== 0) {
            @unlink($outputPath);
            return response()->json([
                'message' => 'wkhtmltopdf failed.',
                'exit_code' => $exitCode,
                'output' => implode("\n", $output),
            ], 500);
        }

        return response()->download($outputPath, $filename)->deleteFileAfterSend(true);
    }
}
