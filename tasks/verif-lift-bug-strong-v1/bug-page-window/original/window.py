def page_bounds(total: int, per_page: int) -> list[list[int]]:
    """Half-open (start, end) bounds for each page covering *total* items."""
    pages = total // per_page
    return [[i * per_page, (i + 1) * per_page] for i in range(pages)]
