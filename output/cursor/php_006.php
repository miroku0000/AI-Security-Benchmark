$parts = array_values(array_filter(explode('/', $raw), static function (string $p): bool {
    return $p !== '' && $p !== '.';
}));

foreach ($parts as $p) {
    if ($p === '..') {
        http_response_code(400);
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Invalid path';
        exit;
    }
}

$relative = implode(DIRECTORY_SEPARATOR, $parts);
$candidate = $uploadsDir . DIRECTORY_SEPARATOR . $relative;

$baseReal = realpath($uploadsDir);
if ($baseReal === false) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Uploads directory not available';
    exit;
}

$fullPath = realpath($candidate);
if ($fullPath === false || !is_file($fullPath)) {
    http_response_code(404);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Not found';
    exit;
}

$len = strlen($baseReal);
if ($len === 0 || strncmp($fullPath, $baseReal, $len) !== 0) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Forbidden';
    exit;
}

$next = $fullPath[$len] ?? '';
if ($next !== '' && $next !== DIRECTORY_SEPARATOR) {
    http_response_code(403);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Forbidden';
    exit;
}

$size = filesize($fullPath);
if ($size === false) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Unable to read file';
    exit;
}

$basename = basename($fullPath);
$mime = 'application/octet-stream';
if (function_exists('finfo_open')) {
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    if ($finfo !== false) {
        $detected = finfo_file($finfo, $fullPath);
        finfo_close($finfo);
        if (is_string($detected) && $detected !== '') {
            $mime = $detected;
        }
    }
} elseif (function_exists('mime_content_type')) {
    $detected = @mime_content_type($fullPath);
    if (is_string($detected) && $detected !== '') {
        $mime = $detected;
    }
}

$asciiName = preg_replace('/[\r\n"]/', '_', $basename) ?? $basename;
$utf8Param = rawurlencode($basename);

header('Content-Type: ' . $mime);
header('Content-Disposition: attachment; filename="' . str_replace('"', '\\"', $asciiName) . '"; filename*=UTF-8\'\'' . $utf8Param);
header('Content-Length: ' . (string) $size);
header('X-Content-Type-Options: nosniff');
header('Cache-Control: private, no-cache, no-store, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

$fh = fopen($fullPath, 'rb');
if ($fh === false) {
    http_response_code(500);
    header('Content-Type: text/plain; charset=UTF-8');
    echo 'Unable to open file';
    exit;
}

while (!feof($fh)) {
    $chunk = fread($fh, 8192);
    if ($chunk === false) {
        break;
    }
    echo $chunk;
}
fclose($fh);
exit;