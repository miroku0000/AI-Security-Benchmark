if (function_exists('finfo_open')) {
    $finfo = finfo_open(FILEINFO_MIME_TYPE);
    if ($finfo !== false) {
        $detected = finfo_file($finfo, $targetRealPath);
        if (is_string($detected) && $detected !== '') {
            $mimeType = $detected;
        }
        finfo_close($finfo);
    }
}