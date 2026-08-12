import unittest

from incremental_load import run_load

# Two runs in which every partition produces rows, and every row is newer than
# everything the previous run saw.
BATCH_1 = [
    {"row_id": "r1", "partition": "north", "event_ts": "2026-05-01T10:00:00"},
    {"row_id": "r2", "partition": "south", "event_ts": "2026-05-01T11:00:00"},
]

BATCH_2 = [
    {"row_id": "r3", "partition": "north", "event_ts": "2026-05-02T10:00:00"},
    {"row_id": "r4", "partition": "south", "event_ts": "2026-05-02T11:00:00"},
]


class TestRunLoad(unittest.TestCase):
    def test_first_run_loads_everything(self):
        report = run_load(BATCH_1, {})
        self.assertEqual(sorted(report["loaded"]), ["r1", "r2"])
        self.assertEqual(report["status"], "success")

    def test_second_run_loads_only_the_new_rows(self):
        first = run_load(BATCH_1, {})
        second = run_load(BATCH_1 + BATCH_2, first["state"])
        self.assertEqual(sorted(second["loaded"]), ["r3", "r4"])

    def test_no_row_is_loaded_twice(self):
        first = run_load(BATCH_1, {})
        second = run_load(BATCH_1 + BATCH_2, first["state"])
        self.assertEqual(set(first["loaded"]) & set(second["loaded"]), set())

    def test_reports_no_stale_partitions_when_all_advance(self):
        report = run_load(BATCH_1, {})
        self.assertEqual(report["stale_partitions"], [])


if __name__ == "__main__":
    unittest.main()
