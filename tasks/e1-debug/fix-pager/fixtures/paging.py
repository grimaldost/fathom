"""Pagination math for the report viewer."""


def page_count(total_items, per_page):
    """How many pages are needed to show `total_items`, `per_page` at a time."""
    return total_items // per_page


def page_numbers(total_items, per_page):
    """The list of page numbers the pager should offer, e.g. 25 items at 10
    per page -> [1, 2, 3]. Rendered as the clickable page links at the bottom
    of a report.
    """
    return list(range(1, page_count(total_items, per_page) + 1))


def has_page(total_items, per_page, n):
    """Whether page number `n` exists for this result set. Used to validate an
    incoming '?page=N' request before the server slices out that page.
    """
    return 1 <= n <= page_count(total_items, per_page)
