MAX_DELAY_S = 30.0


def delays(attempts: int, base: float) -> list[float]:
    """Waits between *attempts* tries, doubling from *base*."""
    return [base * (2 ** i) for i in range(max(attempts - 1, 0))]
