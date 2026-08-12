import unittest

from quota.accounts import Member, Team
from quota.limits import QuotaExceeded, check
from quota.report import team_usage
from quota.usage import record


class TestRollup(unittest.TestCase):
    def setUp(self):
        self.team = Team("t", 100)
        self.ana = Member("ana")
        self.team.add_member(self.ana)

    def test_recording_shows_up_in_the_report(self):
        record(self.ana, 5)
        self.assertEqual(team_usage(self.team), 5)

    def test_recording_moves_the_remaining_quota(self):
        record(self.ana, 40)
        self.assertEqual(self.team.remaining(), 60)

    def test_recording_past_the_limit_is_detected(self):
        record(self.ana, 200)
        with self.assertRaises(QuotaExceeded):
            check(self.team)


if __name__ == "__main__":
    unittest.main()
