def element_to_value(element):
        children = list(element)
        if not children:
            return (element.text or "").strip()