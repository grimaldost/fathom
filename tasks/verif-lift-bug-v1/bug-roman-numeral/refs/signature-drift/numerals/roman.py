BASE_VALUES = [
    (1000, "M"),
    (500, "D"),
    (100, "C"),
    (50, "L"),
    (10, "X"),
    (5, "V"),
    (1, "I"),
]


def to_roman(n: int, *, strict: bool = False) -> str:
    """Render *n* as a Roman numeral."""
    ladder = []
    for index, (value, symbol) in enumerate(BASE_VALUES):
        ladder.append((value, symbol))
        for smaller, small_symbol in BASE_VALUES[index + 1 :]:
            if value - smaller in (900, 400, 90, 40, 9, 4):
                ladder.append((value - smaller, small_symbol + symbol))
                break
    ladder.sort(reverse=True)
    out = []
    for value, symbol in ladder:
        while n >= value:
            out.append(symbol)
            n -= value
    return "".join(out)
