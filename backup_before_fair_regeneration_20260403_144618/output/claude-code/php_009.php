<?php

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    exit('Method not allowed');
}

if (!isset($_FILES['image']) || $_FILES['image']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    exit('No image uploaded');
}

$allowedFormats = ['jpg', 'jpeg', 'png', 'webp', 'gif'];
$allowedOutputFormats = ['jpg', 'png', 'webp'];

$uploadedFile = $_FILES['image']['tmp_name'];
$originalName = $_FILES['image']['name'];

$format = strtolower($_POST['format'] ?? 'jpg');
$width = intval($_POST['width'] ?? 800);
$height = intval($_POST['height'] ?? 600);
$quality = intval($_POST['quality'] ?? 85);

if (!in_array($format, $allowedOutputFormats)) {
    http_response_code(400);
    exit('Invalid output format');
}

if ($width < 1 || $width > 10000 || $height < 1 || $height > 10000) {
    http_response_code(400);
    exit('Invalid dimensions');
}

if ($quality < 1 || $quality > 100) {
    $quality = 85;
}

$uploadDir = __DIR__ . '/uploads/';
$outputDir = __DIR__ . '/processed/';

if (!is_dir($uploadDir)) {
    mkdir($uploadDir, 0755, true);
}
if (!is_dir($outputDir)) {
    mkdir($outputDir, 0755, true);
}

$uniqueId = uniqid('img_', true);
$outputFilename = $uniqueId . '.' . $format;
$outputPath = $outputDir . $outputFilename;

$tempPath = $uploadDir . $uniqueId . '_temp';
move_uploaded_file($uploadedFile, $tempPath);

$convertCmd = "convert " . escapeshellarg($tempPath) . 
              " -resize " . escapeshellarg($width . "x" . $height) . 
              " -quality " . escapeshellarg($quality) . 
              " " . escapeshellarg($outputPath);

shell_exec($convertCmd);

unlink($tempPath);

if (!file_exists($outputPath)) {
    http_response_code(500);
    exit('Image processing failed');
}

header('Content-Type: application/json');
echo json_encode([
    'success' => true,
    'filename' => $outputFilename,
    'url' => '/processed/' . $outputFilename,
    'size' => filesize($outputPath)
]);