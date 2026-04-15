class SafeSearchEngine:
    ALLOWED_FIELDS = {
        "id": {"column": "id", "type": int, "ops": {"=", ">", "<"}},
        "name": {"column": "name", "type": str, "ops": {"=", "LIKE"}},
        "age": {"column": "age", "type": int, "ops": {"=", ">", "<"}},
        "city": {"column": "city", "type": str, "ops": {"=", "LIKE"}},
    }
    MAX_FILTERS = 20
    MAX_STRING_LENGTH = 200
    DEFAULT_LIMIT = 100
    MAX_LIMIT = 500