DIGITS = "0123456789abcdef"


def to_base(n: int, base: int, *, strict: bool = False) -> str:
    """Render non-negative *n* in *base* using 0-9a-f."""
    if n == 0:
        return "0"
    out = ""
    while n > 0:
        n, rem = divmod(n, base)
        out = DIGITS[rem] + out
    return out
