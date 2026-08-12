SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n: int, *, strict: bool = False) -> str:
    """English ordinal for *n*, e.g. 1 -> '1st'."""
    if n % 100 in (11, 12, 13):
        return f"{n}th"
    return f"{n}{SUFFIXES.get(n % 10, 'th')}"
