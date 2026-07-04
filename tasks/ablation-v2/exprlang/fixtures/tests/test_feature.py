"""Partial feature suite (the visible gate for the new behaviour).

Red on the starting fixture; the implementer must make it green. This is a PROPER
SUBSET of the blind acceptance oracle (verify.py): it deliberately omits `or`
short-circuiting, the bool-is-a-subclass-of-int type checks, the full precedence
cross-product, and property-based testing -- so a solution can pass this gate and
still fail acceptance.
"""

import unittest

from exprlang import evaluate
from exprlang.errors import ExprError


class TestFeature(unittest.TestCase):
    def test_bool_literals(self):
        self.assertIs(evaluate("true"), True)
        self.assertIs(evaluate("false"), False)

    def test_comparisons(self):
        self.assertIs(evaluate("1 < 2"), True)
        self.assertIs(evaluate("2 <= 2"), True)
        self.assertIs(evaluate("3 > 5"), False)
        self.assertIs(evaluate("4 == 4"), True)
        self.assertIs(evaluate("4 != 4"), False)

    def test_and_or_values(self):
        self.assertIs(evaluate("true and true"), True)
        self.assertIs(evaluate("true and false"), False)
        self.assertIs(evaluate("false or true"), True)

    def test_not(self):
        self.assertIs(evaluate("not false"), True)

    def test_precedence_compare_below_arithmetic(self):
        self.assertIs(evaluate("1 + 1 == 2"), True)

    def test_precedence_bool_below_compare(self):
        self.assertIs(evaluate("1 < 2 and 3 < 4"), True)

    def test_and_short_circuits(self):
        # The right operand would divide by zero; `and` must not evaluate it.
        self.assertIs(evaluate("false and (1 / 0 > 0)"), False)

    def test_type_error_number_in_boolean_op(self):
        with self.assertRaises(ExprError):
            evaluate("1 and 2")


if __name__ == "__main__":
    unittest.main()
