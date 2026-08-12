"""Shipped suite. Green on the current source: it covers only the common cases
every copy already agrees on, not the rules they have drifted apart on."""

import unittest

from forms.invite import validate_invite
from forms.profile import validate_profile
from forms.signup import validate_signup

VALIDATORS = (validate_signup, validate_profile, validate_invite)


class TestCommonCases(unittest.TestCase):
    def test_a_plain_address_is_accepted_everywhere(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertTrue(fn("a@example.com"))

    def test_a_missing_domain_dot_is_rejected_everywhere(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertFalse(fn("a@example"))

    def test_two_at_signs_are_rejected_everywhere(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertFalse(fn("a@@example.com"))

    def test_an_empty_local_part_is_rejected_everywhere(self):
        for fn in VALIDATORS:
            with self.subTest(fn=fn.__name__):
                self.assertFalse(fn("@example.com"))


if __name__ == "__main__":
    unittest.main()
