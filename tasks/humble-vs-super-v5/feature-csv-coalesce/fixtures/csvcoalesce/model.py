"""Column model for csvcoalesce."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Column:
    """A named column with a coercion type: ``"str"``, ``"int"`` or ``"float"``."""

    name: str
    type: str
