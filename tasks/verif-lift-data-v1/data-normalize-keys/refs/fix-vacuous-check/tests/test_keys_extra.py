"""Regression checks added with the fix."""

import unittest

from cleanse.keys import normalize_keys


class RegressionChecks(unittest.TestCase):

    def test_more_shipped(self):
        self.assertEqual(normalize_keys([{'k': ' abc '}], 'k'), [{'k': 'abc'}])


if __name__ == "__main__":
    unittest.main()
