<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method Not Allowed']);
    exit;
}

if (!isset($_POST['data'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing data']);
    exit;
}

$payload = unserialize(base64_decode((string) $_POST['data']));

if ($payload === false && $_POST['data'] !== '') {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid serialized data']);
    exit;
}

$imported = 0;
if (is_array($payload)) {
    foreach ($payload as $item) {
        $imported++;
    }
} elseif (is_object($payload) || $payload !== null) {
    $imported = 1;
}

echo json_encode([
    'status' => 'ok',
    'imported' => $imported,
]);
