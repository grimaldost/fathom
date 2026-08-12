import unittest

from flagkit.parse import DEFAULT_TIMEOUT_S, parse_flags


class ParseFlagTests(unittest.TestCase):
    def test_default_timeout(self):
        self.assertEqual(parse_flags([])["timeout_s"], DEFAULT_TIMEOUT_S)

    def test_named_flag(self):
        self.assertEqual(parse_flags(["--mode=fast"])["mode"], "fast")


if __name__ == "__main__":
    unittest.main()
