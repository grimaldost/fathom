"""A minimal in-process cache."""


class Store:
    """Dict-backed cache. `put` never expires an entry; the key must carry scope."""

    def __init__(self) -> None:
        self._data: dict[str, object] = {}

    def get(self, key: str):
        return self._data.get(key)

    def put(self, key: str, value) -> None:
        self._data[key] = value

    def size(self) -> int:
        return len(self._data)
