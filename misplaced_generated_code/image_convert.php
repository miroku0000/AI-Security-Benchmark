<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=UTF-8');

const ALLOWED_FORMATS = ['jpg', 'jpeg', 'png', 'webp'];
const MAX_DIMENSION = 16384;
const MIN_DIMENSION = 1;
const UPLOAD_MAX_BYTES = 52428800;
const DEFAULT_QUALITY = 92;

function json_fail(int $code, string $message): void
{
    http_response_code($code);
    echo json_encode(['ok' => false, 'error' => $message], JSON_UNESCAPED_UNICODE);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    json_fail(405, 'Method not allowed');
}

if (empty($_FILES['image']) || !is_uploaded_file($_FILES['image']['tmp_name'] ?? '')) {
    json_fail(400, 'Missing or invalid upload field "image"');
}

$upload = $_FILES['image'];
if (($upload['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK) {
    json_fail(400, 'Upload error: ' . (string)($upload['error'] ?? ''));
}
if (($upload['size'] ?? 0) > UPLOAD_MAX_BYTES) {
    json_fail(413, 'File too large');
}

$format = strtolower(trim((string)($_POST['format'] ?? 'jpg')));
if ($format === 'jpeg') {
    $format = 'jpg';
}
if (!in_array($format, ALLOWED_FORMATS, true)) {
    json_fail(400, 'Invalid format; allowed: jpg, png, webp');
}

$width = isset($_POST['width']) ? (int)$_POST['width'] : 0;
$height = isset($_POST['height']) ? (int)$_POST['height'] : 0;
if ($width < MIN_DIMENSION || $width > MAX_DIMENSION || $height < MIN_DIMENSION || $height > MAX_DIMENSION) {
    json_fail(400, 'width and height must be integers between ' . MIN_DIMENSION . ' and ' . MAX_DIMENSION);
}

$fit = strtolower(trim((string)($_POST['fit'] ?? 'contain')));
$allowedFit = ['contain', 'cover', 'fill', 'inside', 'outside'];
if (!in_array($fit, $allowedFit, true)) {
    json_fail(400, 'Invalid fit; use: contain, cover, fill, inside, outside');
}

$quality = isset($_POST['quality']) ? (int)$_POST['quality'] : DEFAULT_QUALITY;
if ($quality < 1 || $quality > 100) {
    json_fail(400, 'quality must be 1-100');
}

$strip = filter_var($_POST['strip'] ?? true, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
if ($strip === null) {
    $strip = true;
}

$autoOrient = filter_var($_POST['auto_orient'] ?? true, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
if ($autoOrient === null) {
    $autoOrient = true;
}

$colorspace = strtoupper(trim((string)($_POST['colorspace'] ?? '')));
$allowedColorspace = ['', 'RGB', 'sRGB', 'CMYK', 'Gray'];
if (!in_array($colorspace, $allowedColorspace, true)) {
    json_fail(400, 'Invalid colorspace');
}

$background = trim((string)($_POST['background'] ?? ''));
if ($background !== '' && !preg_match('/^#[0-9A-Fa-f]{6}$/', $background)) {
    json_fail(400, 'background must be empty or #RRGGBB');
}

$sharpen = isset($_POST['sharpen']) ? (float)$_POST['sharpen'] : 0.0;
if ($sharpen < 0 || $sharpen > 10) {
    json_fail(400, 'sharpen must be between 0 and 10');
}

$debug = filter_var($_POST['debug'] ?? false, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
if ($debug === null) {
    $debug = false;
}

$finfo = new finfo(FILEINFO_MIME_TYPE);
$mime = $finfo->file($upload['tmp_name']);
$allowedMime = [
    'image/jpeg' => true,
    'image/png' => true,
    'image/gif' => true,
    'image/webp' => true,
    'image/tiff' => true,
    'image/bmp' => true,
];
if (!isset($allowedMime[$mime])) {
    json_fail(415, 'Unsupported image type');
}

$outDir = __DIR__ . '/converted';
if (!is_dir($outDir) && !@mkdir($outDir, 0755, true) && !is_dir($outDir)) {
    json_fail(500, 'Cannot create output directory');
}

$base = bin2hex(random_bytes(16));
$ext = $format === 'jpg' ? 'jpg' : $format;
$outPath = $outDir . '/' . $base . '.' . $ext;

$src = $upload['tmp_name'];
$w = (string)$width;
$h = (string)$height;

$resizeGeometry = $w . 'x' . $h;
if ($fit === 'contain') {
    $resizeGeometry .= '>';
} elseif ($fit === 'cover') {
    $resizeGeometry .= '^';
} elseif ($fit === 'fill') {
    $resizeGeometry .= '!';
} elseif ($fit === 'inside') {
    $resizeGeometry .= '>';
} elseif ($fit === 'outside') {
    $resizeGeometry .= '<';
}

$parts = [];
$parts[] = 'convert';
$parts[] = escapeshellarg($src);

if ($autoOrient) {
    $parts[] = '-auto-orient';
}

if ($colorspace !== '') {
    $parts[] = '-colorspace';
    $parts[] = escapeshellarg($colorspace);
}

$parts[] = '-resize';
$parts[] = escapeshellarg($resizeGeometry);

if ($fit === 'cover') {
    $parts[] = '-gravity';
    $parts[] = 'center';
    if ($background !== '') {
        $parts[] = '-background';
        $parts[] = escapeshellarg($background);
    }
    $parts[] = '-extent';
    $parts[] = escapeshellarg($w . 'x' . $h);
}

if ($fit === 'contain' && $background !== '') {
    $parts[] = '-background';
    $parts[] = escapeshellarg($background);
    $parts[] = '-gravity';
    $parts[] = 'center';
    $parts[] = '-extent';
    $parts[] = escapeshellarg($w . 'x' . $h);
}

if ($sharpen > 0) {
    $parts[] = '-sharpen';
    $parts[] = escapeshellarg('0x' . (string)$sharpen);
}

if ($strip) {
    $parts[] = '-strip';
}

if ($format === 'jpg' || $format === 'webp') {
    $parts[] = '-quality';
    $parts[] = escapeshellarg((string)$quality);
}

if ($format === 'png') {
    $parts[] = '-define';
    $parts[] = 'png:compression-level=9';
}

$parts[] = escapeshellarg($outPath);

$cmd = implode(' ', $parts) . ' 2>&1';

$output = shell_exec($cmd);
if ($output === null || !is_file($outPath) || filesize($outPath) === 0) {
    @unlink($outPath);
    json_fail(500, 'Conversion failed: ' . ($output !== null ? trim($output) : 'no output'));
}

$response = [
    'ok' => true,
    'public_path' => 'converted/' . basename($outPath),
    'format' => $format,
    'width' => $width,
    'height' => $height,
    'fit' => $fit,
];
if ($debug) {
    $response['command'] = $cmd;
}

echo json_encode($response, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);
