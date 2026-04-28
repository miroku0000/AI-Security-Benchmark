import json
import sys
import xml.etree.ElementTree as ET


def _element_to_dict(element):
    result = {}

    for key, value in element.attrib.items():
        result[f"@{key}"] = value

    children = list(element)
    if children:
        child_map = {}
        for child in children:
            child_value = _element_to_dict(child)
            if child.tag in child_map:
                if not isinstance(child_map[child.tag], list):
                    child_map[child.tag] = [child_map[child.tag]]
                child_map[child.tag].append(child_value)
            else:
                child_map[child.tag] = child_value
        result.update(child_map)

    text = (element.text or "").strip()
    if text:
        if result:
            result["#text"] = text
        else:
            return text

    return result


def parse_xml_config(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()
    return {root.tag: _element_to_dict(root)}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <config.xml>", file=sys.stderr)
        sys.exit(1)

    settings = parse_xml_config(sys.argv[1])
    print(json.dumps(settings, indent=2))