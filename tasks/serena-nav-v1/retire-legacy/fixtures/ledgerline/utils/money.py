"""Money value object. DECOY: the method below shares a name with
the core settlement function and is unrelated to it."""


class Money:
    def __init__(self, amount):
        self.amount = float(amount)

    def settle(self):
        """Round this amount for settlement display (unrelated decoy)."""
        return round(self.amount, 2)

    def as_cents(self):
        return int(round(self.amount * 100))
