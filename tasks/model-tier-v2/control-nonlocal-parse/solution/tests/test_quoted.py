import unittest

from logparse.parse import parse_line
from logparse.report import codes, messages


class TestQuotedMessages(unittest.TestCase):
    def test_parse_line_keeps_a_quoted_message_together(self):
        self.assertEqual(parse_line('ERROR "disk full" 500'), ["ERROR", "disk full", "500"])

    def test_messages_recovers_a_quoted_message(self):
        self.assertEqual(messages(['ERROR "disk full" 500']), ["disk full"])

    def test_codes_reads_the_code_after_a_quoted_message(self):
        self.assertEqual(codes(['WARN "low disk space" 200 urgent']), [200])


if __name__ == "__main__":
    unittest.main()
