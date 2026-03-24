def _read_key_from_config(item: Dict[str, Any]) -> str:
    if "key" in item and item["key"]:
        return _normalize_key_material(str(item["key"]))
    if "key_env" in item and item["key_env"]:
        env_value = os.getenv(str(item["key_env"]))
        if not env_value:
            raise JWTConfigurationError(f"Missing key material in env var: {item['key_env']}")
        return _normalize_key_material(env_value)
    if "key_file" in item and item["key_file"]:
        with open(str(item["key_file"]), "r", encoding="utf-8") as handle:
            return handle.read().strip()
    raise JWTConfigurationError(f"Missing key configuration for source: {item.get('name', '<unknown>')}")