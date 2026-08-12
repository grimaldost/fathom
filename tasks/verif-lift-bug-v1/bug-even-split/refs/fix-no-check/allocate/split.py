def split_amount(total: int, parts: int) -> list[int]:
    """Divide *total* into *parts* near-equal integer shares."""
    base, remainder = divmod(total, parts)
    return [base + (1 if i < remainder else 0) for i in range(parts)]
