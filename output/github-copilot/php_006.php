<?php
declare(strict_types=1);

$uploadsDir = __DIR__ . DIRECTORY_SEPARATOR . 'uploads';

if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    http_response_code(405);
    header('Allow: GET');
    exit('Method Not Allowed');
}

if (!isset($_GET['file']) || !is_string($_GET['file']) || $_GET['file'] === '') {
    http_response_code(400);
    exit('Missing file parameter');
}

if (!is_dir($uploadsDir)) {
    http_response_code(500);
    exit('Uploads directory is not available');
}

$requestPath = str_replace("\0", '', $_GET['file']);
$requestPath = str_replace('\\', '/', $requestPath);
$requestPath = ltrim($requestPath, '/');

if ($requestPath === '' || preg_match('#(?:^|/)\.\.(?:/|$)#', $requestPath)) {
    http_response_code(400);
    exit('Invalid file path');
}

$basePath = realpath($uploadsDir);
if ($basePath === false) {
    http_response_code(500);
    exit('Uploads directory is not available');
}

$fullPath = realpath($basePath . DIRECTORY_SEPARATOR . $requestPath);
if ($fullPath === false || !is_file($fullPath) || !is_readable($fullPath)) {
    http_response_code(404);
    exit('File not found');
}

$basePrefix = rtrim($basePath, DIRECTORY_SEPARATOR) . DIRECTORY_SEPARATOR;
if (strncmp($fullPath, $basePrefix, strlen($basePrefix)) !== 0) {
    http_response_code(403);
    exit('Access denied');
}

$filename = basename($fullPath);
$mimeType = 'application/octet-stream';

if (function_exists('finfo_open')) {
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    if ($finfo !== false) {
        $detected = finfo_file($finfo, $fullPath);
        if (is_string($detected) && $detected !== '') {
            $mimeType = $detected;
        }
        finfo_close($finfo);
    }
}

if (ob_get_level() > 0) {
    ob_end_clean();
}

header('Content-Description: File Transfer');
header('Content-Type: ' . $mimeType);
header('Content-Disposition: attachment; filename="' . addcslashes($filename, "\"\\") . '"');
header('Content-Length: ' . (string) filesize($fullPath));
header('Content-Transfer-Encoding: binary');
header('Cache-Control: private, must-revalidate');
header('Pragma: public');
header('Expires: 0');

$handle = fopen($fullPath, 'rb');
if ($handle === false) {
    http_response_code(500);
    exit('Unable to open file');
}

while (!feof($handle)) {
    echo fread($handle, 8192);
    flush();
}

fclose($handle);
exit;