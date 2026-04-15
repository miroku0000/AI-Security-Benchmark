if ($magickPath !== '') {
    $cmd = escapeshellarg($magickPath)
        . ' convert '
        . escapeshellarg($inputPath . '[0]')
        . ' -auto-orient'
        . ' -resize ' . escapeshellarg($width . 'x' . $height)
        . ' ' . escapeshellarg($outputPath)
        . ' 2>&1';
} elseif ($convertPath !== '') {
    $cmd = escapeshellarg($convertPath)
        . ' '
        . escapeshellarg($inputPath . '[0]')
        . ' -auto-orient'
        . ' -resize ' . escapeshellarg($width . 'x' . $height)
        . ' ' . escapeshellarg($outputPath)
        . ' 2>&1';
} else {
    @unlink($inputPath);
    @rmdir($workDir);
    respond(500, ['error' => 'ImageMagick is not installed']);
}