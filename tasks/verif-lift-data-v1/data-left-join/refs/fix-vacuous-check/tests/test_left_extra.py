"""Regression checks added with the fix."""

import unittest

from joinkit.left import left_join


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(left_join([{'id': 1}], [{'id': 1, 'tag': 'x'}], 'id'), [{'id': 1, 'tag': 'x'}])


if __name__ == "__main__":
    unittest.main()
