"""Three-way merge for configuration maps."""

from cfg.merge import MISSING, Conflict, merge
from cfg.nested import merge_tree

__all__ = ["merge", "merge_tree", "Conflict", "MISSING"]
