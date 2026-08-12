def pivot_counts(rows: list[dict], rows_key: str, cols_key: str, columns: list[str], *, strict: bool = False) -> list[dict]:
    """Count rows into a row-key by column-key grid."""
    grid: dict = {}
    for row in rows:
        cell = grid.setdefault(row[rows_key], {})
        cell[row[cols_key]] = cell.get(row[cols_key], 0) + 1
    out = []
    for name in grid:
        entry = {rows_key: name}
        for column in columns:
            entry[column] = grid[name].get(column, 0)
        out.append(entry)
    return out
