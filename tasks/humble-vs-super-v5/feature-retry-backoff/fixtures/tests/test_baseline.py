"""Baseline tests — pass on the unmodified fixture."""

import unittest

from retrier import elapsed


class TestElapsed(unittest.TestCase):
    def test_elapsed_uses_injected_clock(self):
        self.assertEqual(elapsed(10.0, monotonic=lambda: 12.5), 2.5)


if __name__ == "__main__":
    unittest.main()
