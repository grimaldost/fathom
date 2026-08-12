import unittest

from quota.accounts import Member, Team
from quota.report import team_usage
from quota.usage import record


class TestRollup(unittest.TestCase):
    def test_recording_shows_up_in_the_report(self):
        team = Team("t", 100)
        ana = Member("ana")
        team.add_member(ana)
        record(ana, 5)
        self.assertEqual(team_usage(team), 5)


if __name__ == "__main__":
    unittest.main()
