<?php
declare(strict_types=1);

$templatesDir = __DIR__ . '/templates';
$slug = isset($_GET['page']) ? (string) $_GET['page'] : 'home';
$slug = preg_replace('/[^a-zA-Z0-9_-]/', '', $slug) ?: 'home';

$file = $templatesDir . '/' . $slug . '.php';
$realTemplates = realpath($templatesDir);
$realFile = is_file($file) ? realpath($file) : false;

if ($realTemplates === false || $realFile === false || strpos($realFile, $realTemplates) !== 0) {
    http_response_code(404);
    $file = $templatesDir . '/404.php';
    $realFile = is_file($file) ? realpath($file) : false;
    if ($realFile === false || strpos($realFile, $realTemplates) !== 0) {
        header('Content-Type: text/plain; charset=UTF-8');
        echo 'Not found';
        exit;
    }
}

include $realFile;

<?php
declare(strict_types=1);
?><!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Home</title>
</head>
<body>
    <h1>Home</h1>
</body>
</html>

<?php
declare(strict_types=1);
?><!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Not found</title>
</head>
<body>
    <h1>404 — Page not found</h1>
</body>
</html>