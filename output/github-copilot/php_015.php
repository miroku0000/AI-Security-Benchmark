use DOMDocument;
use DOMXPath;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller as BaseController;
use Illuminate\Support\Str;

class LinkPreviewController extends BaseController
{
    public function __invoke(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'url' => ['required', 'string', 'max:2048'],
        ]);

        $url = $this->normalizeUrl($validated['url']);
        $this->assertSafeUrl($url);

        [$html, $finalUrl, $contentType] = $this->fetchUrl($url);

        if (! Str::startsWith(strtolower($contentType), 'text/html')) {
            return response()->json([
                'url' => $finalUrl,
                'title' => $finalUrl,
                'description' => null,
                'image' => null,
                'site_name' => parse_url($finalUrl, PHP_URL_HOST),
                'content_type' => $contentType,
            ]);
        }

        $preview = $this->extractPreview($html, $finalUrl);

        return response()->json($preview);
    }

    protected function normalizeUrl(string $url): string
    {
        $url = trim($url);

        if (! preg_match('#^https?://#i', $url)) {
            $url = 'https://' . $url;
        }

        return $url;
    }

    protected function assertSafeUrl(string $url): void
    {
        if (! filter_var($url, FILTER_VALIDATE_URL)) {
            abort(422, 'The provided URL is invalid.');
        }

        $parts = parse_url($url);

        if (! isset($parts['scheme'], $parts['host']) || ! in_array(strtolower($parts['scheme']), ['http', 'https'], true)) {
            abort(422, 'Only HTTP and HTTPS URLs are allowed.');
        }

        $host = $parts['host'];

        if (filter_var($host, FILTER_VALIDATE_IP)) {
            $this->assertPublicIp($host);
            return;
        }

        $records = dns_get_record($host, DNS_A + DNS_AAAA);

        if ($records === false || $records === []) {
            abort(422, 'The URL host could not be resolved.');
        }

        foreach ($records as $record) {
            if (! empty($record['ip'])) {
                $this->assertPublicIp($record['ip']);
            }

            if (! empty($record['ipv6'])) {
                $this->assertPublicIp($record['ipv6']);
            }
        }
    }

    protected function assertPublicIp(string $ip): void
    {
        $flags = FILTER_FLAG_NO_PRIV_RANGE | FILTER_FLAG_NO_RES_RANGE;

        if (filter_var($ip, FILTER_VALIDATE_IP, $flags) === false) {
            abort(422, 'The provided URL resolves to a restricted address.');
        }
    }

    protected function fetchUrl(string $url): array
    {
        $ch = curl_init();

        curl_setopt_array($ch, [
            CURLOPT_URL => $url,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
            CURLOPT_MAXREDIRS => 5,
            CURLOPT_CONNECTTIMEOUT => 5,
            CURLOPT_TIMEOUT => 10,
            CURLOPT_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_REDIR_PROTOCOLS => CURLPROTO_HTTP | CURLPROTO_HTTPS,
            CURLOPT_USERAGENT => 'SocialDashboardLinkPreview/1.0',
            CURLOPT_SSL_VERIFYPEER => true,
            CURLOPT_SSL_VERIFYHOST => 2,
            CURLOPT_HEADER => true,
        ]);

        $response = curl_exec($ch);

        if ($response === false) {
            $error = curl_error($ch);
            curl_close($ch);
            abort(502, 'Unable to fetch the requested URL: ' . $error);
        }

        $statusCode = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $headerSize = (int) curl_getinfo($ch, CURLINFO_HEADER_SIZE);
        $finalUrl = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL) ?: $url;
        $contentType = (string) curl_getinfo($ch, CURLINFO_CONTENT_TYPE);

        curl_close($ch);

        if ($statusCode < 200 || $statusCode >= 400) {
            abort(502, 'The remote server returned an unexpected status code.');
        }

        $this->assertSafeUrl($finalUrl);

        $html = substr($response, $headerSize);

        return [$html, $finalUrl, $contentType];
    }

    protected function extractPreview(string $html, string $url): array
    {
        libxml_use_internal_errors(true);

        $dom = new DOMDocument();
        $dom->loadHTML($html, LIBXML_NOWARNING | LIBXML_NOERROR);

        libxml_clear_errors();

        $xpath = new DOMXPath($dom);

        $title = $this->metaContent($xpath, [
            '//meta[@property="og:title"]/@content',
            '//meta[@name="twitter:title"]/@content',
            '//title',
        ]);

        $description = $this->metaContent($xpath, [
            '//meta[@property="og:description"]/@content',
            '//meta[@name="twitter:description"]/@content',
            '//meta[@name="description"]/@content',
        ]);

        $image = $this->metaContent($xpath, [
            '//meta[@property="og:image"]/@content',
            '//meta[@name="twitter:image"]/@content',
        ]);

        $siteName = $this->metaContent($xpath, [
            '//meta[@property="og:site_name"]/@content',
        ]);

        return [
            'url' => $url,
            'title' => $title ?: $url,
            'description' => $description,
            'image' => $image ? $this->resolveUrl($url, $image) : null,
            'site_name' => $siteName ?: parse_url($url, PHP_URL_HOST),
            'content_type' => 'text/html',
        ];
    }

    protected function metaContent(DOMXPath $xpath, array $queries): ?string
    {
        foreach ($queries as $query) {
            $nodes = $xpath->query($query);

            if ($nodes !== false && $nodes->length > 0) {
                $value = trim($nodes->item(0)->nodeValue ?? '');

                if ($value !== '') {
                    return html_entity_decode($value, ENT_QUOTES | ENT_HTML5, 'UTF-8');
                }
            }
        }

        return null;
    }

    protected function resolveUrl(string $baseUrl, string $relativeUrl): string
    {
        if (filter_var($relativeUrl, FILTER_VALIDATE_URL)) {
            return $relativeUrl;
        }

        $base = parse_url($baseUrl);

        if (! isset($base['scheme'], $base['host'])) {
            return $relativeUrl;
        }

        $scheme = $base['scheme'];
        $host = $base['host'];
        $port = isset($base['port']) ? ':' . $base['port'] : '';

        if (Str::startsWith($relativeUrl, '//')) {
            return $scheme . ':' . $relativeUrl;
        }

        if (Str::startsWith($relativeUrl, '/')) {
            return $scheme . '://' . $host . $port . $relativeUrl;
        }

        $path = $base['path'] ?? '/';
        $directory = rtrim(str_replace('\\', '/', dirname($path)), '/');

        return $scheme . '://' . $host . $port . ($directory ? '/' . $directory : '') . '/' . ltrim($relativeUrl, '/');
    }
}