"""Slug and anchor helpers for the blog engine."""

import re


def words(text):
    """Break a title into lowercase word tokens."""
    return re.split(r"\s+", text.strip().lower())


def slug(title):
    """URL slug for a post title, e.g. 'Hello World' -> 'hello-world'."""
    # Strip URL-unsafe characters out of each token before joining.
    cleaned = [re.sub(r"[^a-z0-9]+", "", w) for w in words(title)]
    return "-".join(w for w in cleaned if w)


def anchor_id(title):
    """HTML anchor id for an on-page section heading, e.g.
    'Hello World' -> 'sec-hello-world'. Used to build the '#...' links in a
    post's table of contents.
    """
    return "sec-" + "-".join(words(title))
