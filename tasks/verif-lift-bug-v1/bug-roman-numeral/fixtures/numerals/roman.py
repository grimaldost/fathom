BASE_VALUES = [
    (1000, "M"),
    (500, "D"),
    (100, "C"),
    (50, "L"),
    (10, "X"),
    (5, "V"),
    (1, "I"),
]


def to_roman(n: int) -> str:
    """Render *n* as a Roman numeral."""
    ladder = list(BASE_VALUES)
    out = []
    for value, symbol in ladder:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)
