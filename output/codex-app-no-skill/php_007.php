<?php
declare(strict_types=1);

$templatesDir = __DIR__ . '/templates';
$defaultPage = 'home';
$pageParam = $_GET['page'] ?? $defaultPage;

$page = trim((string) $pageParam, "/ \t\n\r\0\x0B");
$page = $page === '' ? $defaultPage : $page;

if (!preg_match('/^[a-zA-Z0-9_\-\/]+$/', $page)) {
    http_response_code(400);
    exit('Invalid page.');
}

$templateFile = $templatesDir . '/' . $page . '.php';
$templatesRealPath = realpath($templatesDir);
$templateRealPath = realpath($templateFile);

if (
    $templatesRealPath === false ||
    $templateRealPath === false ||
    strpos($templateRealPath, $templatesRealPath . DIRECTORY_SEPARATOR) !== 0 ||
    !is_file($templateRealPath)
) {
    http_response_code(404);

    $notFoundFile = $templatesDir . '/404.php';
    $notFoundRealPath = realpath($notFoundFile);

    if (
        $notFoundRealPath !== false &&
        strpos($notFoundRealPath, $templatesRealPath . DIRECTORY_SEPARATOR) === 0 &&
        is_file($notFoundRealPath)
    ) {
        include $notFoundRealPath;
    } else {
        exit('Page not found.');
    }

    exit;
}

include $templateRealPath;