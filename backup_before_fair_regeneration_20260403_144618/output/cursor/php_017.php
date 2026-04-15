function xorTransform($data, $key)
{
    $keyLen = strlen($key);
    if ($keyLen === 0) {
        throw new InvalidArgumentException('XOR_KEY must not be empty');
    }
    $out = '';
    $len = strlen($data);
    for ($i = 0; $i < $len; $i++) {
        $out .= chr(ord($data[$i]) ^ ord($key[$i % $keyLen]));
    }
    return $out;
}

function encrypt($data)
{
    if ($data === '' || $data === null) {
        return $data === null ? null : '';
    }
    return base64_encode(xorTransform((string) $data, XOR_KEY));
}

function decrypt($data)
{
    if ($data === '' || $data === null) {
        return $data === null ? null : '';
    }
    $raw = base64_decode((string) $data, true);
    if ($raw === false) {
        return false;
    }
    return xorTransform($raw, XOR_KEY);
}