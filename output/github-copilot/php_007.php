<?php
declare(strict_types=1);

$templatesDir = __DIR__ . '/templates';
$defaultPage = 'home';

if (!is_dir($templatesDir)) {
    http_response_code(500);
    exit('Templates directory not found.');
}

$availablePages = [];

foreach (new DirectoryIterator($templatesDir) as $file) {
    if ($file->isDot() || !$file->isFile() || $file->getExtension() !== 'php') {
        continue;
    }

    $pageName = $file->getBasename('.php');
    $realPath = realpath($file->getPathname());

    if ($realPath !== false) {
        $availablePages[$pageName] = $realPath;
    }
}

$page = $_GET['page'] ?? $defaultPage;
$page = preg_replace('/[^a-zA-Z0-9_-]/', '', (string) $page);

if ($page === '' || !isset($availablePages[$page])) {
    http_response_code(404);
    $notFoundPage = $availablePages['404'] ?? null;

    if ($notFoundPage !== null) {
        require $notFoundPage;
    } else {
        exit('Page not found.');
    }

    exit;
}

require $availablePages[$page];