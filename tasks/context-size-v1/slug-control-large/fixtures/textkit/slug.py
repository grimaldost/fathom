"""Slugify titles for URLs."""

import re


def slugify(title):
    """Turn a title into a URL slug."""
    s = title.lower()
    s = re.sub(r"[^a-z0-9]", "-", s)
    return s
