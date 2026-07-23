"""Tag-string normalization for tagkit.

See the package README for the full contract that ``normalize_tags`` is meant to
satisfy.
"""


def normalize_tags(raw):
    """Turn a comma-separated tag string into a normalized list of tags.

    Each piece is split on commas, stripped of surrounding whitespace, folded to
    lowercase, and dropped if it is empty after stripping. The order in which the
    tags first appear is preserved.
    """
    tags = []
    for piece in raw.split(","):
        tag = piece.strip().lower()
        if tag:
            tags.append(tag)
    return tags
