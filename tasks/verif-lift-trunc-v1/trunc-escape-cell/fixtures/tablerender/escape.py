"""Escaping for pipe-delimited table rendering."""

PIPE = "|"
ESCAPED_PIPE = "\\|"

def escape_cell(value: str) -> str:
    """Escape a body cell for the pipe-delimited renderer."""
    return value.strip()

def pad(value: str, width: int) -> str:
    """Pad *value* to *width* for a fixed-width column."""
    return value + " " * max(width - len(value), 0)


def join_row(cells: list) -> str:
    """Join already-escaped *cells* into one rendered row."""
    return PIPE + PIPE.join(cells) + PIPE


def rule(widths: list) -> str:
    """The dashed rule under a header row."""
    return PIPE + PIPE.join("-" * width for width in widths) + PIPE


def escape_header(value: str) -> str:
    """Escape a header cell for the pipe-delimited renderer."""
    return value.strip().upper()
