def flatten(items: list) -> list:
    """Depth-first leaves of a nested list."""
    out = []
    for item in items:
        if isinstance(item, list):
            inner = flatten(item)
            out.append(inner[0] if inner else None)
        else:
            out.append(item)
    return out
