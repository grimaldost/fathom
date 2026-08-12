import unittest

from cfg.merge import Conflict, merge
from cfg.nested import merge_tree


class TestMerge(unittest.TestCase):
    def test_a_one_sided_change_wins(self):
        self.assertEqual(merge({"a": 1}, {"a": 2}, {"a": 1}), {"a": 2})
        self.assertEqual(merge({"a": 1}, {"a": 1}, {"a": 3}), {"a": 3})

    def test_untouched_keys_survive(self):
        self.assertEqual(
            merge({"a": 1, "b": 2}, {"a": 1, "b": 2}, {"a": 9, "b": 2}), {"a": 9, "b": 2}
        )

    def test_different_changes_conflict(self):
        self.assertEqual(merge({"a": 1}, {"a": 2}, {"a": 3}), {"a": Conflict(1, 2, 3)})


class TestMergeTree(unittest.TestCase):
    def test_a_one_sided_nested_change_wins(self):
        base = {"db": {"host": "h", "port": 1}}
        ours = {"db": {"host": "h", "port": 2}}
        self.assertEqual(merge_tree(base, ours, base), {"db": {"host": "h", "port": 2}})

    def test_different_nested_changes_conflict(self):
        base = {"db": {"port": 1}}
        ours = {"db": {"port": 2}}
        theirs = {"db": {"port": 3}}
        self.assertEqual(merge_tree(base, ours, theirs), {"db": {"port": Conflict(1, 2, 3)}})


if __name__ == "__main__":
    unittest.main()
