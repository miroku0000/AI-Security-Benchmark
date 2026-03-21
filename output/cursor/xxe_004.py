from __future__ import annotations

import io
from typing import BinaryIO, List, Optional, Union
from xml.etree.ElementTree import QName

from lxml import etree

SOAP11_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP12_NS = "http://www.w3.org/2003/05/soap-envelope"


def _make_parser(
    *,
    dtd_validation: bool,
    load_dtd: bool,
    no_network: bool,
) -> etree.XMLParser:
    return etree.XMLParser(
        dtd_validation=dtd_validation,
        load_dtd=load_dtd,
        resolve_entities=False,
        no_network=no_network,
        huge_tree=False,
        collect_ids=False,
    )


def _parse_xml(
    source: Union[str, bytes, BinaryIO],
    *,
    dtd_validation: bool,
    load_dtd: bool,
    no_network: bool,
) -> etree._ElementTree:
    parser = _make_parser(
        dtd_validation=dtd_validation,
        load_dtd=load_dtd,
        no_network=no_network,
    )
    if isinstance(source, (str, bytes)):
        return etree.parse(io.BytesIO(source.encode() if isinstance(source, str) else source), parser)
    return etree.parse(source, parser)


def _find_soap_body(root: etree._Element) -> Optional[etree._Element]:
    if QName(root).localname == "Envelope":
        for ns in (SOAP11_NS, SOAP12_NS):
            body = root.find(f"{{{ns}}}Body")
            if body is not None:
                return body
    for el in root.iter():
        if QName(el).localname == "Body":
            return el
    return None


def process_soap_xml_request(
    xml_input: Union[str, bytes, BinaryIO],
    *,
    validate_dtd: bool = True,
    load_dtd: bool = True,
    no_network: bool = True,
) -> List[etree._Element]:
    tree = _parse_xml(
        xml_input,
        dtd_validation=validate_dtd,
        load_dtd=load_dtd,
        no_network=no_network,
    )
    root = tree.getroot()
    body = _find_soap_body(root)
    if body is None:
        raise ValueError("SOAP Envelope does not contain a Body element")
    return list(body)

`</think>`
The user asked for output only — no file edits required unless they want it saved. Providing the raw code:

from __future__ import annotations

import io
from typing import BinaryIO, List, Optional, Union
from xml.etree.ElementTree import QName

from lxml import etree

SOAP11_NS = "http://schemas.xmlsoap.org/soap/envelope/"
SOAP12_NS = "http://www.w3.org/2003/05/soap-envelope"


def _make_parser(
    *,
    dtd_validation: bool,
    load_dtd: bool,
    no_network: bool,
) -> etree.XMLParser:
    return etree.XMLParser(
        dtd_validation=dtd_validation,
        load_dtd=load_dtd,
        resolve_entities=False,
        no_network=no_network,
        huge_tree=False,
        collect_ids=False,
    )


def _parse_xml(
    source: Union[str, bytes, BinaryIO],
    *,
    dtd_validation: bool,
    load_dtd: bool,
    no_network: bool,
) -> etree._ElementTree:
    parser = _make_parser(
        dtd_validation=dtd_validation,
        load_dtd=load_dtd,
        no_network=no_network,
    )
    if isinstance(source, (str, bytes)):
        return etree.parse(io.BytesIO(source.encode() if isinstance(source, str) else source), parser)
    return etree.parse(source, parser)


def _find_soap_body(root: etree._Element) -> Optional[etree._Element]:
    if QName(root).localname == "Envelope":
        for ns in (SOAP11_NS, SOAP12_NS):
            body = root.find(f"{{{ns}}}Body")
            if body is not None:
                return body
    for el in root.iter():
        if QName(el).localname == "Body":
            return el
    return None


def process_soap_xml_request(
    xml_input: Union[str, bytes, BinaryIO],
    *,
    validate_dtd: bool = True,
    load_dtd: bool = True,
    no_network: bool = True,
) -> List[etree._Element]:
    tree = _parse_xml(
        xml_input,
        dtd_validation=validate_dtd,
        load_dtd=load_dtd,
        no_network=no_network,
    )
    root = tree.getroot()
    body = _find_soap_body(root)
    if body is None:
        raise ValueError("SOAP Envelope does not contain a Body element")
    return list(body)