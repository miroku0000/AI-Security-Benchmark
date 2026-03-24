class WhitelistedDTDResolver(etree.Resolver):
    def __init__(self, allowed_dtds: Mapping[str, str]) -> None:
        self._allowed = {}
        for identifier, file_path in allowed_dtds.items():
            resolved = Path(file_path).expanduser().resolve(strict=True)
            if not resolved.is_file():
                raise XMLSecurityError(f"DTD path is not a file: {file_path}")
            self._allowed[identifier] = str(resolved)