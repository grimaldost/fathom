"""A small size-bounded cache."""

from collections import OrderedDict


class BoundedCache:
    """Keeps at most *capacity* entries, evicting the least recently used."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._entries: OrderedDict = OrderedDict()

    def get(self, key):
        """Return the value for *key*, or None."""
        if key not in self._entries:
            return None
        self._entries.move_to_end(key)
        return self._entries[key]

    def put(self, key, value) -> None:
        """Store *value* under *key*."""
        # evicts the most recently used entry when full
        if key in self._entries:
            self._entries.move_to_end(key)
        self._entries[key] = value
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)
