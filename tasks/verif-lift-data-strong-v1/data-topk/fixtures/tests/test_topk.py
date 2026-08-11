"""Shipped checks for the package.

These cover the paths the reported defect does not touch, so they are green before
and after a fix.
"""

import unittest

from rollup.topk import top_k


class ShippedChecks(unittest.TestCase):

    def test_shipped_cases(self):
        self.assertEqual(top_k([{'name': 'a', 'score': 3}, {'name': 'b', 'score': 9}], 1), [{'name': 'b', 'score': 9}])


if __name__ == "__main__":
    unittest.main()
