import unittest

from cfg.merge import merge


class TestAgreedChange(unittest.TestCase):
    def test_the_same_change_on_both_sides_is_not_a_conflict(self):
        self.assertEqual(merge({"a": 1}, {"a": 2}, {"a": 2}), {"a": 2})


if __name__ == "__main__":
    unittest.main()
