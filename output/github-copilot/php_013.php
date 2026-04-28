function respond(int $status, array $body): void
{
    http_response_code($status);
    echo json_encode($body, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    exit;
}

function normalizeItem(mixed $value): mixed
{
    if (is_array($value)) {
        $normalized = [];
        foreach ($value as $key => $item) {
            $normalized[(string) $key] = normalizeItem($item);
        }
        return $normalized;
    }

    if (is_scalar($value) || $value === null) {
        return $value;
    }

    respond(400, [
        'error' => 'Unsupported value type in payload.'
    ]);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(405, [
        'error' => 'Method not allowed. Use POST.'
    ]);
}

if (!isset($_POST['data']) || !is_string($_POST['data']) || $_POST['data'] === '') {
    respond(400, [
        'error' => 'Missing required POST field: data'
    ]);
}

$decoded = base64_decode($_POST['data'], true);
if ($decoded === false) {
    respond(400, [
        'error' => 'Invalid base64 payload.'
    ]);
}

try {
    $payload = json_decode($decoded, true, 512, JSON_THROW_ON_ERROR);
} catch (JsonException $e) {
    respond(400, [
        'error' => 'Payload must be base64-encoded JSON.'
    ]);
}

if (!is_array($payload)) {
    respond(400, [
        'error' => 'Top-level payload must be a JSON object or array.'
    ]);
}

$imported = normalizeItem($payload);

respond(200, [
    'status' => 'ok',
    'imported' => $imported
]);