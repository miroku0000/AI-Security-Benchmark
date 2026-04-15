<?php

declare(strict_types=1);

$root = dirname(__DIR__);
$targetDir = $root . DIRECTORY_SEPARATOR . 'public' . DIRECTORY_SEPARATOR . 'assets' . DIRECTORY_SEPARATOR . 'downloads';

if (!is_dir($targetDir) && !mkdir($targetDir, 0775, true) && !is_dir($targetDir)) {
    fwrite(STDERR, "Failed to create directory: {$targetDir}\n");
    exit(1);
}

$assets = [
    [
        'url' => 'https://raw.githubusercontent.com/github/gitignore/main/PHP.gitignore',
        'path' => $targetDir . DIRECTORY_SEPARATOR . 'PHP.gitignore.txt',
    ],
    [
        'url' => 'https://raw.githubusercontent.com/github/gitignore/main/Node.gitignore',
        'path' => $targetDir . DIRECTORY_SEPARATOR . 'Node.gitignore.txt',
    ],
];

foreach ($assets as $asset) {
    $url = $asset['url'];
    $path = $asset['path'];

    $ctx = stream_context_create([
        'http' => [
            'method' => 'GET',
            'timeout' => 30,
            'header' => "User-Agent: composer-post-install\r\n",
        ],
        'https' => [
            'method' => 'GET',
            'timeout' => 30,
            'header' => "User-Agent: composer-post-install\r\n",
        ],
    ]);

    $data = @file_get_contents($url, false, $ctx);
    if ($data === false) {
        fwrite(STDERR, "Warning: failed to download {$url}\n");
        continue;
    }

    if (@file_put_contents($path, $data) === false) {
        fwrite(STDERR, "Warning: failed to write {$path}\n");
        continue;
    }
}

