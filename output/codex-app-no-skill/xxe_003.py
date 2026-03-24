def _limit_tree_complexity(root: ET.Element, max_depth: int, max_elements: int) -> None:
    count = 0
    stack = [(root, 1)]
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > max_elements:
            raise XMLValidationError(f"XML contains too many elements (limit: {max_elements})")
        if depth > max_depth:
            raise XMLValidationError(f"XML exceeds maximum nesting depth (limit: {max_depth})")
        children = list(node)
        for child in reversed(children):
            stack.append((child, depth + 1))