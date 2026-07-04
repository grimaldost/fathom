"""Baseline tests - equality filtering only. Pass on the unmodified fixture and
must keep passing after the full engine is added."""

import unittest

from querytable import where


class TestBaselineEquality(unittest.TestCase):
    def test_equality_filter(self):
        rows = [{"a": 1}, {"a": 2}, {"a": 1}]
        self.assertEqual(where(rows, "a", "=", 1), [{"a": 1}, {"a": 1}])

    def test_equality_excludes_none(self):
        rows = [{"a": 1}, {"a": None}]
        self.assertEqual(where(rows, "a", "=", 1), [{"a": 1}])

    def test_does_not_mutate_input(self):
        rows = [{"a": 1}, {"a": 2}]
        where(rows, "a", "=", 1)
        self.assertEqual(rows, [{"a": 1}, {"a": 2}])


if __name__ == "__main__":
    unittest.main()
