function parseUploadedXmlConfig(string $xml): array
{
    $xml = trim($xml);

    if ($xml === '') {
        throw new InvalidArgumentException('The uploaded XML configuration is empty.');
    }

    if (preg_match('/<!DOCTYPE|<!ENTITY/i', $xml) === 1) {
        throw new InvalidArgumentException('DTD and entity declarations are not allowed in uploaded XML configuration files.');
    }

    $previousUseInternalErrors = libxml_use_internal_errors(true);

    try {
        $root = simplexml_load_string(
            $xml,
            SimpleXMLElement::class,
            LIBXML_NONET | LIBXML_NOCDATA | LIBXML_COMPACT
        );

        if ($root === false) {
            throw new RuntimeException(buildXmlErrorMessage(libxml_get_errors()));
        }

        $settingsNode = isset($root->settings) ? $root->settings : $root;

        return extractSettings($settingsNode);
    } finally {
        libxml_clear_errors();
        libxml_use_internal_errors($previousUseInternalErrors);
    }
}

function extractSettings(SimpleXMLElement $node): array
{
    $settings = [];

    foreach ($node->children() as $child) {
        $key = getNodeKey($child);
        $value = extractNodeValue($child);

        if (array_key_exists($key, $settings)) {
            if (!is_array($settings[$key]) || !isListArray($settings[$key])) {
                $settings[$key] = [$settings[$key]];
            }
            $settings[$key][] = $value;
            continue;
        }

        $settings[$key] = $value;
    }

    return $settings;
}

function extractNodeValue(SimpleXMLElement $node): mixed
{
    $children = $node->children();

    if (count($children) === 0) {
        $attributes = getAttributes($node);

        if (array_key_exists('value', $attributes)) {
            return castValue($attributes['value'], $attributes['type'] ?? null);
        }

        return castValue(trim((string) $node), $attributes['type'] ?? null);
    }

    $result = [];

    foreach ($children as $child) {
        $key = getNodeKey($child);
        $value = extractNodeValue($child);

        if (array_key_exists($key, $result)) {
            if (!is_array($result[$key]) || !isListArray($result[$key])) {
                $result[$key] = [$result[$key]];
            }
            $result[$key][] = $value;
            continue;
        }

        $result[$key] = $value;
    }

    return $result;
}

function getNodeKey(SimpleXMLElement $node): string
{
    $attributes = getAttributes($node);

    if ($node->getName() === 'setting') {
        $name = trim($attributes['name'] ?? '');
        if ($name === '') {
            throw new RuntimeException('Each <setting> element must include a non-empty name attribute.');
        }
        return $name;
    }

    $name = trim($attributes['name'] ?? '');
    return $name !== '' ? $name : $node->getName();
}

function getAttributes(SimpleXMLElement $node): array
{
    $attributes = [];

    foreach ($node->attributes() as $name => $value) {
        $attributes[(string) $name] = (string) $value;
    }

    return $attributes;
}

function castValue(string $value, ?string $type): mixed
{
    $type = $type !== null ? strtolower(trim($type)) : null;
    $value = trim($value);

    if ($type === null || $type === '') {
        return normalizeScalar($value);
    }

    return match ($type) {
        'string' => $value,
        'int', 'integer' => filter_var($value, FILTER_VALIDATE_INT) !== false
            ? (int) $value
            : throw new RuntimeException("Invalid integer value: {$value}"),
        'float', 'double' => is_numeric($value)
            ? (float) $value
            : throw new RuntimeException("Invalid float value: {$value}"),
        'bool', 'boolean' => match (strtolower($value)) {
            '1', 'true', 'yes', 'on' => true,
            '0', 'false', 'no', 'off' => false,
            default => throw new RuntimeException("Invalid boolean value: {$value}"),
        },
        'null' => null,
        'json' => decodeJsonValue($value),
        default => throw new RuntimeException("Unsupported setting type: {$type}"),
    };
}

function normalizeScalar(string $value): mixed
{
    $lower = strtolower($value);

    return match (true) {
        $lower === 'true' => true,
        $lower === 'false' => false,
        $lower === 'null' => null,
        preg_match('/^-?(?:0|[1-9][0-9]*)$/', $value) === 1 => (int) $value,
        preg_match('/^-?(?:0|[1-9][0-9]*)\.[0-9]+(?:e[+\-]?[0-9]+)?$/i', $value) === 1 => (float) $value,
        preg_match('/^-?(?:0|[1-9][0-9]*)(?:e[+\-]?[0-9]+)$/i', $value) === 1 => (float) $value,
        default => $value,
    };
}

function decodeJsonValue(string $value): mixed
{
    try {
        return json_decode($value, true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException $e) {
        throw new RuntimeException('Invalid JSON setting value: ' . $e->getMessage(), 0, $e);
    }
}

function buildXmlErrorMessage(array $errors): string
{
    $messages = [];

    foreach ($errors as $error) {
        $messages[] = trim($error->message);
    }

    if ($messages === []) {
        return 'Invalid XML configuration.';
    }

    return 'Invalid XML configuration: ' . implode(' ', $messages);
}

function isListArray(array $value): bool
{
    $index = 0;

    foreach (array_keys($value) as $key) {
        if ($key !== $index) {
            return false;
        }
        $index++;
    }

    return true;
}

if (PHP_SAPI === 'cli') {
    if (!isset($argv[1])) {
        fwrite(STDERR, "Usage: php {$argv[0]} /path/to/config.xml\n");
        exit(1);
    }

    $xml = @file_get_contents($argv[1]);

    if ($xml === false) {
        fwrite(STDERR, "Unable to read XML file: {$argv[1]}\n");
        exit(1);
    }

    try {
        $settings = parseUploadedXmlConfig($xml);
        echo json_encode($settings, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES), PHP_EOL;
        exit(0);
    } catch (Throwable $e) {
        fwrite(STDERR, $e->getMessage() . PHP_EOL);
        exit(1);
    }
}

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Use POST with an uploaded XML file in the "config" field.']);
    exit;
}

if (!isset($_FILES['config'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing uploaded file in the "config" field.']);
    exit;
}

if ($_FILES['config']['error'] !== UPLOAD_ERR_OK) {
    http_response_code(400);
    echo json_encode(['error' => 'File upload failed with error code ' . $_FILES['config']['error'] . '.']);
    exit;
}

if (!is_uploaded_file($_FILES['config']['tmp_name'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid uploaded file.']);
    exit;
}

$xml = @file_get_contents($_FILES['config']['tmp_name']);

if ($xml === false) {
    http_response_code(400);
    echo json_encode(['error' => 'Unable to read uploaded XML file.']);
    exit;
}

try {
    $settings = parseUploadedXmlConfig($xml);
    echo json_encode(['settings' => $settings], JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    http_response_code(400);
    echo json_encode(['error' => $e->getMessage()]);
}