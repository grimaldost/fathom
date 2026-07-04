"""Visit reports over a stream of page URLs."""

from collections import Counter

from urlstats.normalize import page_key


def page_counts(urls):
    """Return a Counter of visits per page."""
    return Counter(page_key(u) for u in urls)


def top_page(urls):
    """Return the most-visited page (ties broken by first appearance), or None."""
    counts = Counter()
    for u in urls:
        counts[page_key(u)] += 1
    return counts.most_common(1)[0][0] if counts else None
