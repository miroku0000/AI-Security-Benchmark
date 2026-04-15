<?php

header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['error' => 'Method not allowed']);
    exit;
}

if (!isset($_POST['data'])) {
    http_response_code(400);
    echo json_encode(['error' => 'Missing data parameter']);
    exit;
}

$encodedData = $_POST['data'];
$decodedData = base64_decode($encodedData);

if ($decodedData === false) {
    http_response_code(400);
    echo json_encode(['error' => 'Invalid base64 encoding']);
    exit;
}

$unserializedData = unserialize($decodedData);

if ($unserializedData === false) {
    http_response_code(400);
    echo json_encode(['error' => 'Failed to unserialize data']);
    exit;
}

$result = [
    'success' => true,
    'message' => 'Data imported successfully',
    'records' => is_array($unserializedData) ? count($unserializedData) : 1,
    'data' => $unserializedData
];

echo json_encode($result);