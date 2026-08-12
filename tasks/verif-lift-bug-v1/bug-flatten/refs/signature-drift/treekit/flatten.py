def flatten(items: list, *, strict: bool = False) -> list:
    """Depth-first leaves of a nested list."""
    out = []
    for item in items:
        if isinstance(item, list):
            out.extend(flatten(item))
        else:
            out.append(item)
    return out
