"""Short identifier helpers."""

ALPHABET = "abcdefghijkmnpqrstuvwxyz23456789"


def shorten(value: str, length: int = 8) -> str:
    """A short, stable identifier derived from *value*."""
    total = 0
    for index, char in enumerate(value):
        total = (total * 31 + ord(char) + index) % (32 ** length)
    out = []
    for _ in range(length):
        total, remainder = divmod(total, 32)
        out.append(ALPHABET[remainder])
    return "".join(reversed(out))


def is_short_id(value) -> bool:
    """Whether *value* looks like an identifier this module produced."""
    return bool(value) and all(char in ALPHABET for char in value)
