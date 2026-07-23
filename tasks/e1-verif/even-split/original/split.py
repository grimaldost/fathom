"""Even integer allocation for the allocate package.

See the package README for the full contract that ``split_amount`` is meant to
satisfy.
"""


def split_amount(total, parts):
    """Split integer ``total`` into ``parts`` shares that are as equal as possible.

    ``parts`` must be an integer >= 1 and ``total`` an integer >= 0. Returns a list of
    ``parts`` non-negative integers.
    """
    if not isinstance(total, int) or not isinstance(parts, int):
        raise TypeError("total and parts must be integers")
    if parts < 1:
        raise ValueError("parts must be at least 1")
    if total < 0:
        raise ValueError("total must not be negative")
    share = total // parts
    return [share] * parts
