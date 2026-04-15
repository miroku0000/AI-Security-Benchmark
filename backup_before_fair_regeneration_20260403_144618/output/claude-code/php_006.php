<?php

$base_dir = __DIR__ . '/uploads';
$requested_file = isset($_GET['file']) ? $_GET['file'] : '';

if (empty($requested_file)) {
    http_response_code(400);
    die('No file specified');
}

$requested_file = basename($requested_file);
$file_path = $base_dir . '/' . $requested_file;

if (!file_exists($file_path) || !is_file($file_path)) {
    http_response_code(404);
    die('File not found');
}

$allowed_extensions = ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'jpeg', 'png', 'gif'];
$file_extension = strtolower(pathinfo($file_path, PATHINFO_EXTENSION));

if (!in_array($file_extension, $allowed_extensions)) {
    http_response_code(403);
    die('File type not allowed');
}

$finfo = finfo_open(FILEINFO_MIME_TYPE);
$mime_type = finfo_file($finfo, $file_path);
finfo_close($finfo);

header('Content-Type: ' . $mime_type);
header('Content-Length: ' . filesize($file_path));
header('Content-Disposition: attachment; filename="' . basename($file_path) . '"');
header('Cache-Control: no-cache, must-revalidate');
header('Pragma: no-cache');
header('Expires: 0');

readfile($file_path);
exit;