def column_widths(header: list[str], rows: list[list[str]], *, strict: bool = False) -> list[int]:
    """Longest cell per column, header included."""
    widths = [len(cell) for cell in header]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    return widths
