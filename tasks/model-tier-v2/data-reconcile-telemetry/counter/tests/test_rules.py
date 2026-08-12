"""Added by the symptom patch: the worked example, and nothing else."""

import unittest

from recon.match import match
from recon.model import Device, Reading


class TestWorkedExample(unittest.TestCase):
    def test_the_worked_example_comes_out_right(self):
        readings = [Reading(2, 140, 6.0), Reading(1, 100, 5.0)]
        devices = [Device("d1", 120, 25)]
        self.assertEqual(match(readings, devices), [(1, "d1")])


if __name__ == "__main__":
    unittest.main()
