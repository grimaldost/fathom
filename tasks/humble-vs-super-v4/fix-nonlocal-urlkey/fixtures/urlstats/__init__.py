"""Count page visits from a stream of request URLs."""

from urlstats.normalize import page_key
from urlstats.report import page_counts, top_page

__all__ = ["page_key", "page_counts", "top_page"]
