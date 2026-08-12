"""Added by the reference solution: the rules the worked example turns on."""

import unittest

from recon.gaps import gaps
from recon.match import match
from recon.model import Device, Reading
from recon.report import summarise


class TestRules(unittest.TestCase):
    def test_the_tolerance_bound_is_inclusive(self):
        readings = [Reading(1, 100, 5.0)]
        self.assertEqual(match(readings, [Device("d1", 110, 10)]), [(1, "d1")])

    def test_the_nearest_device_wins(self):
        readings = [Reading(1, 100, 5.0)]
        devices = [Device("d1", 108, 10), Device("d2", 102, 10)]
        self.assertEqual(match(readings, devices), [(1, "d2")])

    def test_a_tie_prefers_the_earlier_then_lower_id(self):
        readings = [Reading(1, 100, 5.0)]
        devices = [Device("d9", 105, 10), Device("d1", 95, 10)]
        self.assertEqual(match(readings, devices), [(1, "d1")])

    def test_the_counts_reconcile(self):
        readings = [Reading(1, 100, 5.0), Reading(2, 9000, 1.0)]
        pairs = match(readings, [Device("d1", 100, 5)])
        gap_ids = gaps(readings, pairs)
        got = summarise(readings, pairs, gap_ids)
        self.assertEqual(got["matched"] + got["gaps"], got["readings"])


if __name__ == "__main__":
    unittest.main()
