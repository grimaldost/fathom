import unittest

from httpkit import retries


class RetryTests(unittest.TestCase):
    def test_attempts_left(self):
        self.assertEqual(retries.attempts_left(2), 3)

    def test_backoff_doubles(self):
        self.assertEqual(retries.backoff_for(3), 2.0)


if __name__ == "__main__":
    unittest.main()
