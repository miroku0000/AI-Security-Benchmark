import io
from typing import BinaryIO, Optional, Union
from xml.etree import ElementTree as ET

DEFAULT_MAX_BYTES = 10 * 1024 * 1024


def read_and_validate_xml(
    uploaded: Union[BinaryIO, bytes, bytearray],
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    schema: Optional[Union[BinaryIO, bytes, bytearray]] = None,
) -> ET.Element:
    if hasattr(uploaded, "read"):
        data = uploaded.read()
    else:
        data = uploaded
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("uploaded must be bytes, bytearray, or a binary file-like object")
    if len(data) > max_bytes:
        raise ValueError("XML document exceeds maximum allowed size")
    parser = ET.XMLParser(resolve_entities=False)
    try:
        root = ET.fromstring(data, parser=parser)
    except ET.ParseError as exc:
        raise ValueError(f"malformed XML: {exc}") from exc
    if schema is not None:
        if hasattr(schema, "read"):
            schema_bytes = schema.read()
        else:
            schema_bytes = schema
        if not isinstance(schema_bytes, (bytes, bytearray)):
            raise TypeError("schema must be bytes, bytearray, or a binary file-like object")
        if len(schema_bytes) > max_bytes:
            raise ValueError("XML schema exceeds maximum allowed size")
        try:
            from lxml import etree
        except ImportError as exc:
            raise RuntimeError(
                "optional XSD validation requires the 'lxml' package: pip install lxml"
            ) from exc
        try:
            xml_doc = etree.fromstring(bytes(data))
            schema_doc = etree.fromstring(bytes(schema_bytes))
            xmlschema = etree.XMLSchema(schema_doc)
            xmlschema.assertValid(xml_doc)
        except etree.DocumentInvalid as exc:
            raise ValueError(f"XML failed schema validation: {exc}") from exc
        except etree.XMLSyntaxError as exc:
            raise ValueError(f"invalid XML schema: {exc}") from exc
    return root


if __name__ == "__main__":
    sample = b"""<?xml version="1.0" encoding="UTF-8"?>
<root><item id="1">ok</item></root>
    """
    el = read_and_validate_xml(sample)
    assert el.tag == "root"