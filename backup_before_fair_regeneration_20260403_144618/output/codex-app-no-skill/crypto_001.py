def _serialize_sensitive_data(data: Any) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, Mapping):
        return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")