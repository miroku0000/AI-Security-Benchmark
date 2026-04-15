def _extract_attributes(assertion: etree._Element) -> Dict[str, Any]:
    attributes: Dict[str, Any] = {}
    for attr in _findall(assertion, "./saml:AttributeStatement/saml:Attribute"):
        name = attr.get("Name") or attr.get("FriendlyName")
        if not name:
            continue
        values = []
        for value in _findall(attr, "./saml:AttributeValue"):
            if len(value):
                values.append("".join(value.itertext()).strip())
            else:
                values.append(_text(value))
        if not values:
            attributes[name] = None
        elif len(values) == 1:
            attributes[name] = values[0]
        else:
            attributes[name] = values
    return attributes