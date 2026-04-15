<?php

declare(strict_types=1);

$root = dirname(__DIR__);

$envExample = $root . DIRECTORY_SEPARATOR . '.env.example';
$envTemplate = $root . DIRECTORY_SEPARATOR . '.env.template';
$envFile = $root . DIRECTORY_SEPARATOR . '.env';

if (!file_exists($envFile)) {
    $source = null;
    if (file_exists($envTemplate)) {
        $source = $envTemplate;
    } elseif (file_exists($envExample)) {
        $source = $envExample;
    }

    if ($source !== null) {
        if (!@copy($source, $envFile)) {
            fwrite(STDERR, "Warning: failed to create .env from {$source}\n");
        }
    }
}

$dirs = [
    $root . DIRECTORY_SEPARATOR . 'public' . DIRECTORY_SEPARATOR . 'assets',
    $root . DIRECTORY_SEPARATOR . 'public' . DIRECTORY_SEPARATOR . 'assets' . DIRECTORY_SEPARATOR . 'vendor',
    $root . DIRECTORY_SEPARATOR . 'public' . DIRECTORY_SEPARATOR . 'assets' . DIRECTORY_SEPARATOR . 'downloads',
    $root . DIRECTORY_SEPARATOR . 'storage',
    $root . DIRECTORY_SEPARATOR . 'storage' . DIRECTORY_SEPARATOR . 'logs',
];

foreach ($dirs as $dir) {
    if (!is_dir($dir) && !mkdir($dir, 0775, true) && !is_dir($dir)) {
        fwrite(STDERR, "Warning: failed to create directory: {$dir}\n");
    }
}

