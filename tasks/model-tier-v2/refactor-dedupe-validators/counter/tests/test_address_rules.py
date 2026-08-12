"""Added by the partial refactor: only the case the instruction spells out."""

import unittest

from forms.signup import validate_signup


class TestExtraction(unittest.TestCase):
    def test_signup_still_accepts_a_plain_address(self):
        self.assertTrue(validate_signup("a@example.com"))


if __name__ == "__main__":
    unittest.main()
