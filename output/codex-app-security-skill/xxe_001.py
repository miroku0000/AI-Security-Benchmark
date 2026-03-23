def _element_to_value(element: ElementTree.Element) -> Any:
    children = list(element)
    text = (element.text or "").strip()
    attributes = dict(element.attrib)