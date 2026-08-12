"""Shipped suite. Green on the current source: every case it covers has one
obvious device per reading, so neither the bound, the tie-break nor the reading
order can change the answer."""

import unittest

from recon.gaps import gaps
from recon.match import match
from recon.model import Device, Reading

FAR = [Reading(1, 100, 5.0), Reading(2, 900, 6.0)]
DEVICES = [Device("d1", 101, 5), Device("d2", 901, 5)]


class TestObviousCases(unittest.TestCase):
    def test_readings_near_their_devices_match(self):
        self.assertEqual(match(FAR, DEVICES), [(1, "d1"), (2, "d2")])

    def test_a_reading_with_no_device_is_a_gap(self):
        readings = [*FAR, Reading(3, 5000, 1.0)]
        self.assertEqual(gaps(readings, match(readings, DEVICES)), [3])

    def test_no_devices_means_every_reading_is_a_gap(self):
        self.assertEqual(gaps(FAR, match(FAR, [])), [1, 2])


if __name__ == "__main__":
    unittest.main()
