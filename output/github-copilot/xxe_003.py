from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from typing import BinaryIO, Callable, Iterable, TextIO


class XMLValidationError(ValueError):
    pass


_UPLOAD_TYPES = (bytes, bytearray, str)
_FORBIDDEN_XML_PATTERN = re.compile(rb"<!DOCTYPE|<!ENTITY", re.IGNORECASE)
_XML_DECLARATION_PATTERN = re.compile(r"^\s*<\?xml[^>]*\?>", re.IGNORECASE)


def _matches_tag(actual: str, expected: str) -> bool:
    if actual == expected:
        return True
    if actual.startswith("{") and "}" in actual:
        return actual.split("}", 1)[1] == expected
    return False


def _read_uploaded_xml(
    upload: bytes | bytearray | str | BinaryIO | TextIO,
    *,
    max_bytes: int,
) -> bytes | str:
    if max_bytes <= 0:
        raise ValueError("max_bytes must be greater than 0")

    if isinstance(upload, (bytes, bytearray)):
        data = bytes(upload)
        if len(data) > max_bytes:
            raise XMLValidationError(f"XML file is too large; maximum size is {max_bytes} bytes")
        return data

    if isinstance(upload, str):
        if len(upload.encode("utf-8")) > max_bytes:
            raise XMLValidationError(f"XML file is too large; maximum size is {max_bytes} bytes")
        return upload

    if not hasattr(upload, "read"):
        raise TypeError("upload must be bytes, str, or a file-like object")

    try:
        chunk = upload.read(max_bytes + 1)
    except Exception as exc:
        raise XMLValidationError("Failed to read uploaded XML") from exc

    if isinstance(chunk, str):
        if len(chunk.encode("utf-8")) > max_bytes:
            raise XMLValidationError(f"XML file is too large; maximum size is {max_bytes} bytes")
        return chunk

    if not isinstance(chunk, (bytes, bytearray)):
        raise TypeError("file-like object must return bytes or str from read()")

    data = bytes(chunk)
    if len(data) > max_bytes:
        raise XMLValidationError(f"XML file is too large; maximum size is {max_bytes} bytes")
    return data


def read_and_validate_xml(
    upload: bytes | bytearray | str | BinaryIO | TextIO,
    *,
    max_bytes: int = 1_000_000,
    allowed_root: str | None = None,
    required_children: Iterable[str] = (),
    required_root_attributes: Iterable[str] = (),
    validator: Callable[[ET.Element], None] | None = None,
) -> ET.Element:
    payload = _read_uploaded_xml(upload, max_bytes=max_bytes)

    if isinstance(payload, str):
        text = payload.lstrip("\ufeff")
        text = _XML_DECLARATION_PATTERN.sub("", text, count=1)
        if not text.strip():
            raise XMLValidationError("Uploaded XML is empty")
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise XMLValidationError("DTD and entity declarations are not allowed")
        try:
            root = ET.fromstring(text)
        except ET.ParseError as exc:
            raise XMLValidationError(f"Malformed XML: {exc}") from exc
    else:
        data = payload.lstrip(b"\xef\xbb\xbf")
        if not data.strip():
            raise XMLValidationError("Uploaded XML is empty")
        if _FORBIDDEN_XML_PATTERN.search(data):
            raise XMLValidationError("DTD and entity declarations are not allowed")
        try:
            root = ET.fromstring(data)
        except ET.ParseError as exc:
            raise XMLValidationError(f"Malformed XML: {exc}") from exc

    if allowed_root is not None and not _matches_tag(root.tag, allowed_root):
        raise XMLValidationError(f"Unexpected root element: {root.tag!r}")

    for attribute_name in required_root_attributes:
        if attribute_name not in root.attrib:
            raise XMLValidationError(f"Missing required root attribute: {attribute_name!r}")

    for child_name in required_children:
        if not any(_matches_tag(child.tag, child_name) for child in root):
            raise XMLValidationError(f"Missing required child element: {child_name!r}")

    if validator is not None:
        validator(root)

    return root


if __name__ == "__main__":
    sample_xml = io.BytesIO(b'<?xml version="1.0"?><document id="123"><title>Hello</title></document>')
    root = read_and_validate_xml(
        sample_xml,
        allowed_root="document",
        required_children=("title",),
        required_root_attributes=("id",),
    )
    print(root.tag)