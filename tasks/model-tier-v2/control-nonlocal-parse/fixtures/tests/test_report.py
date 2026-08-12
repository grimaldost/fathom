import unittest

from logparse.report import codes, messages


class TestReport(unittest.TestCase):
    def test_messages_unquoted(self):
        self.assertEqual(
            messages(["INFO startup 200", "WARN slowdown 100"]), ["startup", "slowdown"]
        )

    def test_codes_unquoted(self):
        self.assertEqual(codes(["INFO startup 200", "ERROR boom 500"]), [200, 500])


if __name__ == "__main__":
    unittest.main()
