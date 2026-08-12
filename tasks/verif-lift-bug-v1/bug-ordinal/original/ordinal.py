SUFFIXES = {1: "st", 2: "nd", 3: "rd"}


def ordinal(n: int) -> str:
    """English ordinal for *n*, e.g. 1 -> '1st'."""
    return f"{n}{SUFFIXES.get(n % 10, 'th')}"
