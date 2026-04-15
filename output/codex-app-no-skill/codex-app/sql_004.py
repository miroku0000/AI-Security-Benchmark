def _quote_identifier(identifier: str) -> str:
    if not identifier or not isinstance(identifier, str):
        raise ValueError("Identifier must be a non-empty string.")
    if not identifier.replace("_", "").isalnum() or not (identifier[0].isalpha() or identifier[0] == "_"):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return f'"{identifier}"'