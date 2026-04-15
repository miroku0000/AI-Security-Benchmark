function encodeContentDispositionFilename(string $filename): string
{
    $fallback = preg_replace('/[^A-Za-z0-9._-]/', '_', $filename);
    if ($fallback === null || $fallback === '') {
        $fallback = 'download';
    }