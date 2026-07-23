"""Tag-string normalization for tagkit.

See the package README for the full contract that ``normalize_tags`` is meant to
satisfy.
"""


def normalize_tags(raw):
    """Turn a comma-separated tag string into a normalized list of tags.

    Each piece is split on commas, stripped of surrounding whitespace, folded to
    lowercase, and dropped if it is empty after stripping. Only the first occurrence
    of each tag is kept, in the order the tags first appear.
    """
    tags = []
    seen = set()
    for piece in raw.split(","):
        tag = piece.strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        tags.append(tag)
    return tags
