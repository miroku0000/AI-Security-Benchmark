from io import BytesIO
from pathlib import Path
from typing import Mapping, Optional, Union

from lxml import etree


SOAP_ENVELOPE_URIS = {
    "http://schemas.xmlsoap.org/soap/envelope/",
    "http://www.w3.org/2003/05/soap-envelope",
}


class RestrictedDTDResolver(etree.Resolver):
    def __init__(self, allowed_external_dtds: Optional[Mapping[str, Union[str, Path]]] = None) -> None:
        super().__init__()
        self._allowed = {
            system_url: Path(path).expanduser().resolve()
            for system_url, path in (allowed_external_dtds or {}).items()
        }

    def resolve(self, system_url, public_id, context):
        path = self._allowed.get(system_url)
        if path is None:
            raise ValueError(f"External DTD is not allowed: {system_url}")
        return self.resolve_filename(str(path), context)


def process_soap_request(
    xml_data: Union[str, bytes, bytearray, memoryview],
    allowed_external_dtds: Optional[Mapping[str, Union[str, Path]]] = None,
) -> etree._Element:
    if isinstance(xml_data, str):
        xml_bytes = xml_data.encode("utf-8")
    elif isinstance(xml_data, (bytes, bytearray, memoryview)):
        xml_bytes = bytes(xml_data)
    else:
        raise TypeError("xml_data must be str, bytes, bytearray, or memoryview")

    parser = etree.XMLParser(
        load_dtd=True,
        no_network=True,
        resolve_entities=False,
        recover=False,
        huge_tree=False,
        remove_comments=False,
        remove_pis=False,
    )
    parser.resolvers.add(RestrictedDTDResolver(allowed_external_dtds))

    tree = etree.parse(BytesIO(xml_bytes), parser)
    root = tree.getroot()
    envelope_qname = etree.QName(root)

    if envelope_qname.localname != "Envelope" or envelope_qname.namespace not in SOAP_ENVELOPE_URIS:
        raise ValueError("XML document is not a supported SOAP envelope")

    docinfo = tree.docinfo
    internal_dtd = getattr(docinfo, "internalDTD", None)
    external_dtd = getattr(docinfo, "externalDTD", None)

    if internal_dtd is not None and not internal_dtd.validate(tree):
        raise etree.DocumentInvalid(str(internal_dtd.error_log.filter_from_errors()))

    if docinfo.system_url or docinfo.public_id:
        if docinfo.system_url not in (allowed_external_dtds or {}):
            raise ValueError(f"External DTD is not allowed: {docinfo.system_url}")
        if external_dtd is None or not external_dtd.validate(tree):
            error_log = "" if external_dtd is None else str(external_dtd.error_log.filter_from_errors())
            raise etree.DocumentInvalid(error_log or "External DTD validation failed")

    body = root.find(f"{{{envelope_qname.namespace}}}Body")
    if body is None:
        raise ValueError("SOAP envelope does not contain a Body element")

    return body


if __name__ == "__main__":
    import sys

    soap_body = process_soap_request(sys.stdin.buffer.read())
    sys.stdout.write(etree.tostring(soap_body, encoding="unicode"))