from __future__ import annotations

from io import BytesIO
from typing import Optional, Union

from lxml import etree


def process_soap_xml(
    xml_input: Union[str, bytes],
    external_dtd: Optional[Union[str, bytes]] = None,
) -> etree._Element:
    if isinstance(xml_input, str):
        xml_input = xml_input.encode("utf-8")

    parser = etree.XMLParser(
        load_dtd=True,
        dtd_validation=True,
        resolve_entities=False,
        no_network=True,
        huge_tree=False,
    )

    root = etree.fromstring(xml_input, parser)

    if external_dtd is not None:
        dtd_source: Union[BytesIO, str]
        if isinstance(external_dtd, bytes):
            dtd_source = BytesIO(external_dtd)
        else:
            dtd_source = external_dtd
        dtd = etree.DTD(dtd_source)
        if not dtd.validate(root):
            raise etree.DocumentInvalid(dtd.error_log.filter_from_errors())

    nsmap = root.nsmap or {}
    soap_ns = None
    for uri in nsmap.values():
        if uri in (
            "http://schemas.xmlsoap.org/soap/envelope/",
            "http://www.w3.org/2003/05/soap-envelope",
        ):
            soap_ns = uri
            break

    if soap_ns is not None:
        body = root.find(f"{{{soap_ns}}}Body")
    else:
        body = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body")
        if body is None:
            body = root.find("{http://www.w3.org/2003/05/soap-envelope}Body")

    if body is None:
        matches = root.xpath(
            ".//*[local-name()='Body' and ("
            "namespace-uri()='http://schemas.xmlsoap.org/soap/envelope/' or "
            "namespace-uri()='http://www.w3.org/2003/05/soap-envelope'"
            ")]"
        )
        if matches:
            body = matches[0]

    if body is None:
        raise ValueError("SOAP Body element not found")

    return body