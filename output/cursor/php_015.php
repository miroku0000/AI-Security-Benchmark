private const MAX_BYTES = 2097152;

    private const DEFAULT_UA = 'Mozilla/5.0 (compatible; LinkPreview/1.0; +https://example.com/bot)';

    public function preview(Request $request): JsonResponse
    {
        $url = (string) $request->input('url', '');

        if ($url === '') {
            return response()->json(['message' => 'The url field is required.'], 422);
        }

        $fetch = $this->fetchWithCurl($url);

        if (! $fetch['ok']) {
            return response()->json([
                'message' => $fetch['error'] ?? 'Failed to fetch URL.',
                'url' => $url,
            ], $fetch['status'] ?? 422);
        }

        $effectiveUrl = $fetch['effective_url'];
        $html = $fetch['body'];
        $meta = $this->parsePreviewMeta($html, $effectiveUrl);

        $payload = [
            'url' => $effectiveUrl,
            'title' => $meta['title'],
            'description' => $meta['description'],
            'image' => $meta['image'],
            'site_name' => $meta['site_name'],
            'type' => $meta['type'],
        ];

        return response()->json($payload);
    }

    /**
     * @return array{ok: bool, body?: string, effective_url?: string, status?: int, error?: string}
     */
    private function fetchWithCurl(string $url): array
    {
        $ch = curl_init();
        if ($ch === false) {
            return ['ok' => false, 'status' => 500, 'error' => 'Could not initialize cURL.'];
        }

        $writeBuffer = '';

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => false,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS => 5,
            CURLOPT_TIMEOUT => 20,
            CURLOPT_CONNECTTIMEOUT => 10,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_REDIR_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_USERAGENT => self::DEFAULT_UA,
            CURLOPT_ENCODING => '',
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_WRITEFUNCTION => function ($curl, $chunk) use (&$writeBuffer): int {
                $writeBuffer .= $chunk;
                if (strlen($writeBuffer) > self::MAX_BYTES) {
                    return 0;
                }

                return strlen($chunk);
            },
        ]);

        $executed = curl_exec($ch);
        $errno = curl_errno($ch);
        $errstr = curl_error($ch);
        $httpCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $effective = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
        curl_close($ch);

        if ($executed === false) {
            return [
                'ok' => false,
                'status' => 422,
                'error' => $errno !== 0 ? ($errstr ?: 'cURL error.') : 'Request failed.',
            ];
        }

        if ($httpCode < 200 || $httpCode >= 400) {
            return [
                'ok' => false,
                'status' => 422,
                'error' => 'Unexpected HTTP status: ' . $httpCode,
            ];
        }

        if ($writeBuffer === '') {
            return [
                'ok' => false,
                'status' => 422,
                'error' => 'Empty response body.',
            ];
        }

        $effectiveUrl = is_string($effective) && $effective !== '' ? $effective : $url;

        return [
            'ok' => true,
            'body' => $writeBuffer,
            'effective_url' => $effectiveUrl,
        ];
    }

    /**
     * @return array{title: ?string, description: ?string, image: ?string, site_name: ?string, type: ?string}
     */
    private function parsePreviewMeta(string $html, string $baseUrl): array
    {
        $out = [
            'title' => null,
            'description' => null,
            'image' => null,
            'site_name' => null,
            'type' => null,
        ];

        $prev = libxml_use_internal_errors(true);
        $doc = new DOMDocument();
        $loaded = $doc->loadHTML('<?xml encoding="UTF-8">' . $html, LIBXML_NOWARNING | LIBXML_NOERROR);
        libxml_clear_errors();
        libxml_use_internal_errors($prev);

        if (! $loaded) {
            return $out;
        }

        $xp = new DOMXPath($doc);

        $getMeta = static function (DOMXPath $xp, string $property): ?string {
            $nodes = $xp->query("//meta[@property='{$property}']/@content | //meta[@name='{$property}']/@content");
            if ($nodes !== false && $nodes->length > 0) {
                $v = trim((string) $nodes->item(0)?->nodeValue);

                return $v !== '' ? $v : null;
            }

            return null;
        };

        $out['title'] = $getMeta($xp, 'og:title')
            ?? $getMeta($xp, 'twitter:title');

        if ($out['title'] === null) {
            $titles = $xp->query('//title');
            if ($titles !== false && $titles->length > 0) {
                $t = trim((string) $titles->item(0)?->textContent);
                $out['title'] = $t !== '' ? $t : null;
            }
        }

        $out['description'] = $getMeta($xp, 'og:description')
            ?? $getMeta($xp, 'twitter:description')
            ?? $getMeta($xp, 'description');

        $imageRaw = $getMeta($xp, 'og:image')
            ?? $getMeta($xp, 'twitter:image')
            ?? $getMeta($xp, 'twitter:image:src');

        if ($imageRaw !== null) {
            $out['image'] = $this->resolveUrl($baseUrl, $imageRaw);
        }

        $out['site_name'] = $getMeta($xp, 'og:site_name')
            ?? $getMeta($xp, 'application-name');

        $out['type'] = $getMeta($xp, 'og:type');

        return $out;
    }

    private function resolveUrl(string $base, string $relative): string
    {
        if (preg_match('#^https?://#i', $relative)) {
            return $relative;
        }

        if (str_starts_with($relative, '//')) {
            $scheme = parse_url($base, PHP_URL_SCHEME) ?: 'https';

            return $scheme . ':' . $relative;
        }

        $baseParts = parse_url($base);
        if ($baseParts === false || ! isset($baseParts['scheme'], $baseParts['host'])) {
            return $relative;
        }

        $scheme = $baseParts['scheme'];
        $host = $baseParts['host'];
        $port = isset($baseParts['port']) ? ':' . $baseParts['port'] : '';
        $origin = $scheme . '://' . $host . $port;

        if (str_starts_with($relative, '/')) {
            return $origin . $relative;
        }

        $path = $baseParts['path'] ?? '/';
        $dir = str_ends_with($path, '/') ? $path : (dirname($path) === '\\' || dirname($path) === '.' ? '/' : dirname($path) . '/');
        if ($dir !== '/' && ! str_ends_with($dir, '/')) {
            $dir .= '/';
        }

        return $origin . $dir . $relative;
    }
}