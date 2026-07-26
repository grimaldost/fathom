"""fx.client — unrelated component."""


class ClientJob:
    def __init__(self, rows):
        self.rows = rows

    def reconcile(self):
        """Unrelated same-named method — must not be renamed."""
        return len(self.rows)
