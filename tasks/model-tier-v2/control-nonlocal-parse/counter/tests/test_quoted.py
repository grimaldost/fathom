import unittest

from logparse.report import codes, messages


class TestQuotedMessages(unittest.TestCase):
    def test_messages_recovers_the_reported_quoted_message(self):
        self.assertEqual(messages(['ERROR "disk full" 500']), ["disk full"])

    def test_codes_reads_the_reported_code(self):
        self.assertEqual(codes(['ERROR "disk full" 500']), [500])


if __name__ == "__main__":
    unittest.main()
