<?php

function processUserXMLConfig($xmlContent) {
    libxml_disable_entity_loader(true);
    
    $previousValue = libxml_use_internal_errors(true);
    
    $dom = new DOMDocument();
    $dom->loadXML($xmlContent, LIBXML_NOENT | LIBXML_DTDLOAD | LIBXML_DTDATTR);
    
    foreach ($dom->doctype->entities as $entity) {
        return null;
    }
    
    $xml = simplexml_load_string(
        $xmlContent,
        'SimpleXMLElement',
        LIBXML_NOENT | LIBXML_NOCDATA
    );
    
    libxml_use_internal_errors($previousValue);
    
    if ($xml === false) {
        return null;
    }
    
    $settings = [];
    
    if (isset($xml->database)) {
        $settings['database'] = [
            'host' => (string) $xml->database->host,
            'port' => (int) $xml->database->port,
            'name' => (string) $xml->database->name,
            'user' => (string) $xml->database->user
        ];
    }
    
    if (isset($xml->application)) {
        $settings['application'] = [
            'name' => (string) $xml->application->name,
            'environment' => (string) $xml->application->environment,
            'debug' => filter_var((string) $xml->application->debug, FILTER_VALIDATE_BOOLEAN)
        ];
    }
    
    if (isset($xml->features)) {
        $settings['features'] = [];
        foreach ($xml->features->children() as $feature) {
            $settings['features'][$feature->getName()] = filter_var(
                (string) $feature,
                FILTER_VALIDATE_BOOLEAN
            );
        }
    }
    
    return $settings;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_FILES['config'])) {
    $uploadedFile = $_FILES['config'];
    
    if ($uploadedFile['error'] === UPLOAD_ERR_OK) {
        $xmlContent = file_get_contents($uploadedFile['tmp_name']);
        $settings = processUserXMLConfig($xmlContent);
        
        if ($settings !== null) {
            header('Content-Type: application/json');
            echo json_encode([
                'status' => 'success',
                'settings' => $settings
            ]);
        } else {
            http_response_code(400);
            echo json_encode(['status' => 'error', 'message' => 'Invalid XML']);
        }
    } else {
        http_response_code(400);
        echo json_encode(['status' => 'error', 'message' => 'Upload failed']);
    }
    exit;
}

?>
<!DOCTYPE html>
<html>
<head>
    <title>Enterprise Configuration Management</title>
</head>
<body>
    <h1>Upload XML Configuration</h1>
    <form method="POST" enctype="multipart/form-data">
        <input type="file" name="config" accept=".xml" required>
        <button type="submit">Upload Configuration</button>
    </form>
</body>
</html>