function normalizeValue(mixed $value, int $depth = 0): mixed
{
    if ($depth > 64) {
        throw new RuntimeException('Payload exceeds maximum nesting depth');
    }