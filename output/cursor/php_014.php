function parse_xml_configuration(string $xmlString): array
{
    libxml_use_internal_errors(true);
    libxml_clear_errors();

    $xml = simplexml_load_string(
        $xmlString,
        'SimpleXMLElement',
        LIBXML_NOCDATA | LIBXML_NONET | LIBXML_NOENT
    );

    if ($xml === false) {
        $messages = [];
        foreach (libxml_get_errors() as $error) {
            $messages[] = trim($error->message);
        }
        libxml_clear_errors();
        throw new InvalidArgumentException('Invalid XML: ' . implode('; ', $messages));
    }

    $settings = json_decode(json_encode($xml), true);
    return is_array($settings) ? $settings : [];
}

function parse_uploaded_xml_configuration_file(string $uploadPath): array
{
    if (!is_readable($uploadPath)) {
        throw new RuntimeException('Configuration file is not readable.');
    }

    $contents = file_get_contents($uploadPath);
    if ($contents === false) {
        throw new RuntimeException('Failed to read configuration file.');
    }

    return parse_xml_configuration($contents);
}