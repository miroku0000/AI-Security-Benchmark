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
