"""Regression checks added with the fix."""

import unittest

from cleanse.keys import normalize_keys


class RegressionChecks(unittest.TestCase):

    def test_reported_defect(self):
        self.assertEqual(normalize_keys([{'k': 'ABC'}], 'k'), [{'k': 'abc'}])

        self.assertEqual(normalize_keys([{'k': ' MiXeD '}], 'k'), [{'k': 'mixed'}])

    def test_related_cases(self):
        self.assertEqual(normalize_keys([{'k': '   '}], 'k'), [{'k': None}])

        self.assertEqual(normalize_keys([{'k': ''}], 'k'), [{'k': None}])


if __name__ == "__main__":
    unittest.main()
