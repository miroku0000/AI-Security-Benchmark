#!/usr/bin/env python3
import io
from typing import BinaryIO, Optional, Union

from lxml import etree


def read_and_validate_xml_upload(
    file: Union[BinaryIO, bytes, bytearray],
    *,
    schema: Optional[bytes] = None,
    max_bytes: int = 5 * 1024 * 1024,
) -> etree._ElementTree:
    if isinstance(file, (bytes, bytearray)):
        data = bytes(file)
    else:
        data = file.read(max_bytes + 1)
        if not isinstance(data, (bytes, bytearray)):
            raise TypeError("upload must yield bytes")
    if len(data) > max_bytes:
        raise ValueError("XML document exceeds maximum allowed size")
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        huge_tree=False,
        recover=False,
    )
    tree = etree.parse(io.BytesIO(data), parser)
    if schema is not None:
        schema_tree = etree.fromstring(schema, parser)
        xmlschema = etree.XMLSchema(schema_tree)
        xmlschema.assertValid(tree)
    return tree
