"""Acceptance verifier for fix-quota-rollup (harness-side, scenario-blind).

Reads the candidate's work ONLY from ``argv[1]`` (the result-view). Its task-constant
references — the stashed buggy original (``original/usage.py``) and the shipped suite
(``original/tests/``) — come from this task directory; both are identical for every
arm, so reading them leaks no scenario identity (ADR-0003).

Cross-module invariant. ``usage.record`` mutates a member without going through
``Team.add_usage``, so the rollup goes stale and everything that reads it is wrong.
The instruction names one reader (``report.team_usage``); a guard there — summing the
members instead of reading the rollup — fixes the reported number and leaves
``Team.remaining`` and ``limits.check`` reading a stale field, which is where the
standard oracle sits. The strong oracle reads the invariant at its source
(``team.used`` against the members' own totals) after an interleaving the instruction
never describes, so patching every reader in turn does not satisfy it.

Oracle levels (``../oracles.toml``): thin ⊂ standard ⊂ strong. The exit code gates
on ``standard`` only.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import bankverify` resolves

import bankverify as bv  # noqa: E402

PACKAGE = "quota"
MODULE = "usage.py"
BUGGY_ORIGINAL = HERE / "original" / "usage.py"
SHIPPED_TESTS = HERE / "original" / "tests"

STANDARD = [
    "member_usage_recorded",
    "team_usage_reported",
    "remaining_reflects_usage",
    "over_quota_detected",
    "no_regression",
    "regression_test_present",
]


class _Pkg:
    """The candidate's modules, imported once."""

    def __init__(self, view: Path):
        self.accounts = bv.import_candidate(view, "quota.accounts", PACKAGE)
        self.usage = bv.import_candidate(view, "quota.usage", PACKAGE)
        self.report = bv.import_candidate(view, "quota.report", PACKAGE)
        self.limits = bv.import_candidate(view, "quota.limits", PACKAGE)

    def team(self, limit, *names):
        team = self.accounts.Team("t", limit)
        members = []
        for name in names:
            member = self.accounts.Member(name)
            team.add_member(member)
            members.append(member)
        return team, members


def _member_recorded(pkg) -> bool:
    _team, (ana,) = pkg.team(100, "ana")
    pkg.usage.record(ana, 5)
    return ana.used == 5


def _team_usage_reported(pkg) -> bool:
    team, (ana,) = pkg.team(100, "ana")
    pkg.usage.record(ana, 5)
    return pkg.report.team_usage(team) == 5


def _remaining_reflects_usage(pkg) -> bool:
    team, (ana, bo) = pkg.team(100, "ana", "bo")
    pkg.usage.record(ana, 5)
    pkg.usage.record(bo, 15)
    return team.remaining() == 80


def _over_quota_detected(pkg) -> bool:
    team, (ana,) = pkg.team(10, "ana")
    pkg.usage.record(ana, 5)
    pkg.limits.check(team)  # under the limit: must not raise
    pkg.usage.record(ana, 20)
    try:
        pkg.limits.check(team)
    except pkg.limits.QuotaExceeded:
        return True
    return False


def _invariant_at_source(pkg) -> bool:
    """The rollup itself, after an interleaving the instruction never describes."""
    team, (ana, bo, cy) = pkg.team(500, "ana", "bo", "cy")
    steps = [(ana, 10), (bo, 5), (ana, 7), (cy, 100), (bo, -3), (ana, -10), (cy, 2)]
    for member, amount in steps:
        pkg.usage.record(member, amount)
        if team.used != sum(m.used for m in team.members):
            return False
    return team.used == 111


def _invariant_with_a_late_member(pkg) -> bool:
    """A member charged before joining, then attached: the rollup must absorb them."""
    team, (ana,) = pkg.team(500, "ana")
    late = pkg.accounts.Member("late")
    pkg.usage.record(ana, 20)
    pkg.usage.record(late, 30)
    team.add_member(late)
    pkg.usage.record(late, 5)
    return team.used == sum(m.used for m in team.members) == 55


def main() -> int:
    if len(sys.argv) != 2:
        print('{"usage_error": false}')
        return 1
    view = Path(sys.argv[1])
    pkg = _Pkg(view)

    results = {
        # --- thin: the anchor plus the reader the instruction names ---------------
        "member_usage_recorded": bv.check(lambda: _member_recorded(pkg)),
        "team_usage_reported": bv.check(lambda: _team_usage_reported(pkg)),
        # --- standard: the two readers the instruction never names ----------------
        "remaining_reflects_usage": bv.check(lambda: _remaining_reflects_usage(pkg)),
        "over_quota_detected": bv.check(lambda: _over_quota_detected(pkg)),
        "no_regression": bv.check(lambda: bv.no_regression(view, SHIPPED_TESTS)),
        "regression_test_present": bv.check(
            lambda: bv.regression_test_present(view, PACKAGE, MODULE, BUGGY_ORIGINAL)
        ),
        # --- strong: the invariant itself, at its source --------------------------
        "rollup_invariant_at_source": bv.check(lambda: _invariant_at_source(pkg)),
        "rollup_invariant_with_late_member": bv.check(lambda: _invariant_with_a_late_member(pkg)),
    }
    return bv.emit(results, STANDARD)


if __name__ == "__main__":
    sys.exit(main())
