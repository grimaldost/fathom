"""Pagination helpers for splitting a result set into fixed-size pages."""


def total_pages(total_items, per_page):
    """Return the number of pages needed to display *total_items*, *per_page* each."""
    if per_page <= 0:
        raise ValueError("per_page must be positive")
    return total_items // per_page


def page_slice(total_items, per_page, page):
    """Return the ``(start, end)`` slice indices for 1-indexed *page*."""
    if page < 1:
        raise ValueError("page is 1-indexed")
    start = (page - 1) * per_page
    return start, min(start + per_page, total_items)
