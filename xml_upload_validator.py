import io
from typing import BinaryIO, Union
from xml.etree import ElementTree as ET


class XMLValidationError(ValueError):
    pass


def read_and_validate_xml(
    upload: Union[bytes, bytearray, BinaryIO],
    *,
    max_bytes: int = 1_048_576,
) -> ET.Element:
    """
    Read bytes from a user upload and ensure the payload is well-formed XML.
    Returns the document root element. Raises XMLValidationError on failure.
    """
    if max_bytes < 1:
        raise XMLValidationError("max_bytes must be positive")

    if isinstance(upload, (bytes, bytearray)):
        data = bytes(upload)
    else:
        chunk = upload.read(max_bytes + 1)
        if not isinstance(chunk, (bytes, bytearray)):
            raise XMLValidationError("upload must yield bytes")
        data = bytes(chunk)
        if len(data) > max_bytes:
            raise XMLValidationError("upload exceeds maximum allowed size")

    if not data:
        raise XMLValidationError("empty XML upload")

    if len(data) > max_bytes:
        raise XMLValidationError("upload exceeds maximum allowed size")

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise XMLValidationError(f"invalid XML: {exc}") from exc

    return root


if __name__ == "__main__":
    sample = b"<root><item>ok</item></root>"
    print(read_and_validate_xml(sample).tag)
