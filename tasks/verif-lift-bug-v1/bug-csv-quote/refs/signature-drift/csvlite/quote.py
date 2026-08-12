def quote_field(value: str, *, strict: bool = False) -> str:
    """Quote *value* for a comma-separated line."""
    if "," in value or "\n" in value or '"' in value:
        return '"' + value.replace('"', '""') + '"'
    return value
