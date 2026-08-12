def quote_field(value: str) -> str:
    """Quote *value* for a comma-separated line."""
    if "," in value or "\n" in value:
        return '"' + value + '"'
    return value
