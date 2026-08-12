import unittest

from quota.accounts import Member, Team
from quota.limits import QuotaExceeded, check
from quota.report import member_usage, team_usage
from quota.usage import record


def team_of(limit, *names):
    team = Team("t", limit)
    members = []
    for name in names:
        member = Member(name)
        team.add_member(member)
        members.append(member)
    return team, members


class TestQuota(unittest.TestCase):
    def test_the_supported_mutation_point_keeps_the_rollup_current(self):
        team, (ana, bo) = team_of(100, "ana", "bo")
        team.add_usage(ana, 30)
        team.add_usage(bo, 20)
        self.assertEqual(team_usage(team), 50)
        self.assertEqual(team.remaining(), 50)

    def test_check_raises_only_over_the_limit(self):
        team, (ana,) = team_of(10, "ana")
        team.add_usage(ana, 5)
        check(team)
        team.add_usage(ana, 20)
        with self.assertRaises(QuotaExceeded):
            check(team)

    def test_record_charges_the_member(self):
        team, (ana,) = team_of(100, "ana")
        record(ana, 7)
        self.assertEqual(member_usage(ana), 7)


if __name__ == "__main__":
    unittest.main()
