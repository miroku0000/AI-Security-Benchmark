@staticmethod
    def _validate_identifier(name: str) -> str:
        if not isinstance(name, str) or not name:
            raise ValueError("Identifier must be a non-empty string")
        if not name.replace("_", "").isalnum() or name[0].isdigit():
            raise ValueError(f"Invalid identifier: {name}")
        return name