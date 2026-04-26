const MAX_UPLOAD_BYTES = 20 * 1024 * 1024;
const MAX_DIMENSION = 8000;
const MIN_DIMENSION = 1;

function h(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function fail(string $message, int $status = 400): never
{
    http_response_code($status);
    renderPage($message);
    exit;
}

function ensureDirectory(string $path): void
{
    if (!is_dir($path) && !mkdir($path, 0755, true) && !is_dir($path)) {
        fail('Failed to create required directory.', 500);
    }
}

function findImageMagickBinary(): string
{
    $candidates = [
        trim((string) shell_exec('command -v magick 2>/dev/null')),
        '/opt/homebrew/bin/magick',
        '/usr/local/bin/magick',
        trim((string) shell_exec('command -v convert 2>/dev/null')),
        '/opt/homebrew/bin/convert',
        '/usr/local/bin/convert',
        '/usr/bin/convert',
    ];

    foreach ($candidates as $candidate) {
        if ($candidate !== '' && is_file($candidate) && is_executable($candidate)) {
            return $candidate;
        }
    }

    fail('ImageMagick is not installed or not available on this server.', 500);
}

function normalizeFormat(string $format): string
{
    $format = strtolower(trim($format));
    $allowed = ['jpg', 'png', 'webp'];

    if (!in_array($format, $allowed, true)) {
        fail('Invalid output format. Allowed formats: jpg, png, webp.');
    }

    return $format;
}

function normalizeDimension(string $value, string $label): int
{
    if (!preg_match('/^\d+$/', $value)) {
        fail("Invalid {$label}. Use a whole number.");
    }

    $dimension = (int) $value;
    if ($dimension < MIN_DIMENSION || $dimension > MAX_DIMENSION) {
        fail("{$label} must be between " . MIN_DIMENSION . ' and ' . MAX_DIMENSION . '.');
    }

    return $dimension;
}

function buildCommand(string $binary, string $sourcePath, string $outputPath, string $format, int $width, int $height): string
{
    $geometry = $width . 'x' . $height;
    $isMagick = basename($binary) === 'magick';

    $parts = [
        escapeshellarg($binary),
    ];

    if ($isMagick) {
        $parts[] = 'convert';
    }

    $parts[] = escapeshellarg($sourcePath . '[0]');
    $parts[] = '-auto-orient';
    $parts[] = '-strip';
    $parts[] = '-resize';
    $parts[] = escapeshellarg($geometry);

    if ($format === 'jpg') {
        $parts[] = '-background';
        $parts[] = escapeshellarg('white');
        $parts[] = '-alpha';
        $parts[] = 'remove';
        $parts[] = '-alpha';
        $parts[] = 'off';
        $parts[] = '-quality';
        $parts[] = '85';
        $parts[] = '-interlace';
        $parts[] = 'Plane';
    } elseif ($format === 'png') {
        $parts[] = '-define';
        $parts[] = escapeshellarg('png:compression-level=9');
    } elseif ($format === 'webp') {
        $parts[] = '-quality';
        $parts[] = '85';
        $parts[] = '-define';
        $parts[] = escapeshellarg('webp:method=6');
    }

    $parts[] = escapeshellarg($outputPath);

    return implode(' ', $parts) . ' 2>&1';
}

function renderPage(?string $message = null, ?string $downloadPath = null, ?string $previewPath = null): void
{
    $messageHtml = $message !== null ? '<p style="padding:12px;background:#f3f4f6;border-radius:8px;">' . h($message) . '</p>' : '';
    $resultHtml = '';

    if ($downloadPath !== null) {
        $safeDownload = h($downloadPath);
        $safePreview = $previewPath !== null ? h($previewPath) : $safeDownload;
        $resultHtml = <<<HTML
        <div style="margin-top:20px;">
            <p><a href="{$safeDownload}" download>Download processed image</a></p>
            <img src="{$safePreview}" alt="Processed image" style="max-width:100%;height:auto;border-radius:8px;border:1px solid #ddd;">
        </div>
        HTML;
    }

    echo <<<HTML
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>ImageMagick Image Processor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="font-family:Arial,sans-serif;background:#fafafa;color:#111;margin:0;padding:32px;">
    <div style="max-width:720px;margin:0 auto;background:#fff;padding:24px;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);">
        <h1 style="margin-top:0;">Image Processor</h1>
        {$messageHtml}
        <form method="post" enctype="multipart/form-data">
            <div style="margin-bottom:16px;">
                <label>Image file<br><input type="file" name="image" accept="image/*" required></label>
            </div>
            <div style="margin-bottom:16px;">
                <label>Output format<br>
                    <select name="format" required>
                        <option value="jpg">jpg</option>
                        <option value="png">png</option>
                        <option value="webp">webp</option>
                    </select>
                </label>
            </div>
            <div style="margin-bottom:16px;">
                <label>Width<br><input type="number" name="width" min="1" max="8000" value="1200" required></label>
            </div>
            <div style="margin-bottom:16px;">
                <label>Height<br><input type="number" name="height" min="1" max="8000" value="1200" required></label>
            </div>
            <button type="submit" style="padding:10px 16px;border:0;border-radius:8px;background:#111;color:#fff;cursor:pointer;">Upload and Process</button>
        </form>
        {$resultHtml}
    </div>
</body>
</html>
HTML;
}

$baseDir = __DIR__;
$uploadDir = $baseDir . '/uploads';
$outputDir = $baseDir . '/processed';

ensureDirectory($uploadDir);
ensureDirectory($outputDir);

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    renderPage();
    exit;
}

if (!isset($_FILES['image']) || !is_array($_FILES['image'])) {
    fail('No file was uploaded.');
}

$file = $_FILES['image'];

if (($file['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
    fail('Upload failed with error code: ' . (string) ($file['error'] ?? 'unknown'));
}

if (!isset($file['tmp_name'], $file['size']) || !is_uploaded_file($file['tmp_name'])) {
    fail('Invalid uploaded file.');
}

if ((int) $file['size'] <= 0 || (int) $file['size'] > MAX_UPLOAD_BYTES) {
    fail('Uploaded file is too large or empty.');
}

$finfo = new finfo(FILEINFO_MIME_TYPE);
$mime = (string) $finfo->file($file['tmp_name']);

$allowedInputMimes = [
    'image/jpeg' => 'jpg',
    'image/png' => 'png',
    'image/webp' => 'webp',
    'image/gif' => 'gif',
    'image/bmp' => 'bmp',
    'image/tiff' => 'tiff',
];

if (!isset($allowedInputMimes[$mime])) {
    fail('Unsupported input image type.');
}

$imageInfo = @getimagesize($file['tmp_name']);
if ($imageInfo === false) {
    fail('The uploaded file is not a valid image.');
}

$format = normalizeFormat((string) ($_POST['format'] ?? ''));
$width = normalizeDimension((string) ($_POST['width'] ?? ''), 'Width');
$height = normalizeDimension((string) ($_POST['height'] ?? ''), 'Height');

$sourceExt = $allowedInputMimes[$mime];
$token = bin2hex(random_bytes(16));
$sourcePath = $uploadDir . '/' . $token . '.' . $sourceExt;
$outputPath = $outputDir . '/' . $token . '.' . $format;

if (!move_uploaded_file($file['tmp_name'], $sourcePath)) {
    fail('Failed to save uploaded file.', 500);
}

$binary = findImageMagickBinary();
$command = buildCommand($binary, $sourcePath, $outputPath, $format, $width, $height);
$commandOutput = (string) shell_exec($command);

if (!is_file($outputPath) || filesize($outputPath) === 0) {
    @unlink($sourcePath);
    @unlink($outputPath);
    fail('Image processing failed. ' . trim($commandOutput), 500);
}

$downloadPath = 'processed/' . basename($outputPath);
renderPage('Image processed successfully.', $downloadPath, $downloadPath);