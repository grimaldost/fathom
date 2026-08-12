def pivot_counts(rows: list[dict], rows_key: str, cols_key: str, columns: list[str]) -> list[dict]:
    """Count rows into a row-key by column-key grid."""
    grid: dict = {}
    for row in rows:
        cell = grid.setdefault(row[rows_key], {})
        cell[row[cols_key]] = 1
    out = []
    for name in grid:
        entry = {rows_key: name}
        for column in columns:
            if column in grid[name]:
                entry[column] = grid[name][column]
        out.append(entry)
    return out
