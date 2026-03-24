def element_to_value(element):
        children = list(element)
        if not children:
            text = (element.text or "").strip()
            return text