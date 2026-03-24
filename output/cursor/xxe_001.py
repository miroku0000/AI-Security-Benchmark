import xml.etree.ElementTree as ET


def parse_xml_config(path):
    tree = ET.parse(path)
    return _element_to_dict(tree.getroot())


def _element_to_dict(element):
    children = list(element)
    if element.attrib:
        out = {"@attributes": dict(element.attrib)}
    else:
        out = {}
    if children:
        for child in children:
            child_data = _element_to_dict(child)
            tag = child.tag
            if tag in out:
                if not isinstance(out[tag], list):
                    out[tag] = [out[tag]]
                out[tag].append(child_data)
            else:
                out[tag] = child_data
        text = (element.text or "").strip()
        if text:
            out["#text"] = text
        return out
    text = (element.text or "").strip()
    if element.attrib:
        if text:
            out["#text"] = text
        return out
    return text if text else None