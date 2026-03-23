def process_soap_request(xml_request: Union[str, bytes]) -> etree._Element:
    if isinstance(xml_request, str):
        xml_request = xml_request.encode("utf-8")
    elif not isinstance(xml_request, (bytes, bytearray)):
        raise TypeError("xml_request must be a str, bytes, or bytearray")