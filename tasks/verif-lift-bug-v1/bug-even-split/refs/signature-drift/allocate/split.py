def split_amount(total: int, parts: int, *, strict: bool = False) -> list[int]:
    """Divide *total* into *parts* near-equal integer shares."""
    base, remainder = divmod(total, parts)
    return [base + (1 if i < remainder else 0) for i in range(parts)]
