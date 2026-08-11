import unittest

from cfg.merge import merge
from cfg.nested import merge_tree


class TestAgreedChange(unittest.TestCase):
    def test_the_same_change_on_both_sides_is_not_a_conflict(self):
        self.assertEqual(merge({"a": 1}, {"a": 2}, {"a": 2}), {"a": 2})

    def test_the_same_nested_change_on_both_sides_is_not_a_conflict(self):
        base = {"db": {"port": 1}}
        edited = {"db": {"port": 2}}
        self.assertEqual(merge_tree(base, edited, edited), {"db": {"port": 2}})


class TestDeletion(unittest.TestCase):
    def test_a_one_sided_deletion_is_applied(self):
        self.assertEqual(merge({"a": 1, "b": 2}, {"b": 2}, {"a": 1, "b": 2}), {"b": 2})

    def test_a_one_sided_nested_deletion_is_applied(self):
        base = {"db": {"port": 1, "host": "h"}}
        ours = {"db": {"host": "h"}}
        self.assertEqual(merge_tree(base, ours, base), {"db": {"host": "h"}})


if __name__ == "__main__":
    unittest.main()
