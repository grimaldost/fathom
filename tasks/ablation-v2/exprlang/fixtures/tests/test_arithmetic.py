"""Baseline suite: the EXISTING arithmetic behaviour that must not regress.

Green on the starting fixture and must stay green after the feature is added.
"""

import unittest

from exprlang import evaluate
from exprlang.errors import EvalError, LexError, ParseError


class TestArithmetic(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(evaluate("42"), 42)
        self.assertEqual(evaluate("3.5"), 3.5)

    def test_precedence(self):
        self.assertEqual(evaluate("1 + 2 * 3"), 7)
        self.assertEqual(evaluate("2 * 3 + 1"), 7)
        self.assertEqual(evaluate("(1 + 2) * 3"), 9)

    def test_left_associative(self):
        self.assertEqual(evaluate("10 - 2 - 3"), 5)
        self.assertEqual(evaluate("100 / 10 / 2"), 5.0)

    def test_unary(self):
        self.assertEqual(evaluate("-5"), -5)
        self.assertEqual(evaluate("--5"), 5)
        self.assertEqual(evaluate("-2 * 3"), -6)

    def test_modulo(self):
        self.assertEqual(evaluate("10 % 3"), 1)

    def test_division_is_float(self):
        self.assertEqual(evaluate("6 / 2"), 3.0)

    def test_variables(self):
        self.assertEqual(evaluate("x + 1", {"x": 10}), 11)

    def test_division_by_zero(self):
        with self.assertRaises(EvalError):
            evaluate("1 / 0")

    def test_modulo_by_zero(self):
        with self.assertRaises(EvalError):
            evaluate("1 % 0")

    def test_unknown_variable(self):
        with self.assertRaises(EvalError):
            evaluate("y")

    def test_bad_syntax(self):
        with self.assertRaises(ParseError):
            evaluate("1 +")

    def test_bad_character(self):
        with self.assertRaises(LexError):
            evaluate("1 $ 2")


if __name__ == "__main__":
    unittest.main()
