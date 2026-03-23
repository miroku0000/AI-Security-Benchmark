def _read_uploaded_xml(
    uploaded: Union[bytes, bytearray, memoryview, BinaryIO, str, os.PathLike],
    *,
    max_bytes: int,
) -> bytes:
    if isinstance(uploaded, (bytes, bytearray, memoryview)):
        data = bytes(uploaded)
    elif isinstance(uploaded, (str, os.PathLike)):
        with open(uploaded, "rb") as f:
            data = f.read(max_bytes + 1)
    elif hasattr(uploaded, "read"):
        data = uploaded.read(max_bytes + 1)
        if isinstance(data, str):
            raise XMLValidationError("Uploaded XML must be read in binary mode, not text mode.")
        if not isinstance(data, (bytes, bytearray)):
            raise XMLValidationError("Uploaded file object returned an unsupported data type.")
        data = bytes(data)
    else:
        raise TypeError("uploaded must be bytes, a binary file-like object, or a filesystem path")