import unittest

from jobkit.runner import is_terminal, message_for


class RunnerTests(unittest.TestCase):
    def test_unknown_state(self):
        self.assertEqual(message_for("nope"), "job unknown")

    def test_terminal_states(self):
        self.assertTrue(is_terminal("failed"))
        self.assertFalse(is_terminal("started"))


if __name__ == "__main__":
    unittest.main()
