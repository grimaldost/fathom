def page_bounds(total: int, per_page: int) -> list[list[int]]:
    """Half-open (start, end) bounds for each page covering *total* items."""
    bounds = []
    start = 0
    while start < total:
        bounds.append([start, min(start + per_page, total)])
        start += per_page
    return bounds
