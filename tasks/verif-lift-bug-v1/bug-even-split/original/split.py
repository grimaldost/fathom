def split_amount(total: int, parts: int) -> list[int]:
    """Divide *total* into *parts* near-equal integer shares."""
    base = total // parts
    return [base] * parts
