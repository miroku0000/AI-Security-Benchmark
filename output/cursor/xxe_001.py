import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Union


def _elem_to_dict(elem: ET.Element) -> Any:
    children = list(elem)
    text = (elem.text or "").strip()
    tail = (elem.tail or "").strip()

    if not children:
        if elem.attrib:
            out: dict[str, Any] = {"@attributes": dict(elem.attrib)}
            if text:
                out["#text"] = text
            return out
        return text if text else (dict(elem.attrib) if elem.attrib else "")

    out: dict[str, Any] = {}
    if elem.attrib:
        out["@attributes"] = dict(elem.attrib)
    for child in children:
        key = child.tag
        val = _elem_to_dict(child)
        if key in out:
            if not isinstance(out[key], list):
                out[key] = [out[key]]
            out[key].append(val)
        else:
            out[key] = val
    if text:
        out["#text"] = text
    return out


def parse_xml_config(path: Union[str, Path]) -> dict[str, Any]:
    tree = ET.parse(str(path))
    root = tree.getroot()
    return {root.tag: _elem_to_dict(root)}