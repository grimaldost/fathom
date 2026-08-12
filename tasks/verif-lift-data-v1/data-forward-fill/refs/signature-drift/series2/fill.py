def forward_fill(values: list, *, strict: bool = False) -> list:
    """Carry the last non-None value forward over each None."""
    out = []
    last = None
    for value in values:
        if value is None:
            out.append(last)
        else:
            last = value
            out.append(value)
    return out
