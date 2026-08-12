"""Added by the reference solution: the rules the three copies had drifted on."""

import unittest

from forms.invite import validate_invite
from forms.profile import validate_profile
from forms.signup import validate_signup

VALIDATORS = (validate_signup, validate_profile, validate_invite)


class TestConvergedRules(unittest.TestCase):
    def test_consecutive_dots_are_rejected_by_every_form(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertFalse(fn("a..b@example.com"))

    def test_a_leading_dot_is_rejected_by_every_form(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertFalse(fn(".a@example.com"))

    def test_comparison_is_case_insensitive_everywhere(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertTrue(fn("A@Example.COM"))
                self.assertFalse(fn(".A@Example.COM"))

    def test_plus_addressing_stays_valid(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertTrue(fn("a+tag@example.com"))


if __name__ == "__main__":
    unittest.main()
