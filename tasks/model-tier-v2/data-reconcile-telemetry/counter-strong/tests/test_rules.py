"""Added by the rules-complete patch."""

import unittest

from recon.match import match
from recon.model import Device, Reading


class TestRules(unittest.TestCase):
    def test_the_tolerance_bound_is_inclusive(self):
        self.assertEqual(match([Reading(1, 100, 5.0)], [Device("d1", 110, 10)]), [(1, "d1")])

    def test_the_nearest_device_wins(self):
        devices = [Device("d1", 108, 10), Device("d2", 102, 10)]
        self.assertEqual(match([Reading(1, 100, 5.0)], devices), [(1, "d2")])


if __name__ == "__main__":
    unittest.main()
