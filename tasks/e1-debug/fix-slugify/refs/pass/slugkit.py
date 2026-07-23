"""Slug and anchor helpers for the blog engine."""

import re


def words(text):
    """Break a title into lowercase word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def slug(title):
    """URL slug for a post title, e.g. 'Hello World' -> 'hello-world'."""
    return "-".join(words(title))


def anchor_id(title):
    """HTML anchor id for an on-page section heading, e.g.
    'Hello World' -> 'sec-hello-world'. Used to build the '#...' links in a
    post's table of contents.
    """
    return "sec-" + "-".join(words(title))
