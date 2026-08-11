"""Tests for the model-tier-v2 tier-separating bank and its three-level oracles.

Stdlib-runnable. This is the bank's admission evidence, produced **before** any paid
spend: for every task it demonstrates offline, through the real verifier, that the
criteria CAN be met and CAN fail, and that each oracle level bites where it claims to.

Four overlays per task, each copied over a fresh copy of ``fixtures/``:

===================  =========================================================
``fixtures/`` alone  the buggy starting state: at least one hard criterion is
                     FALSE, so there is something to fix (violability floor,
                     and the property ``fathom validate`` checks)
``solution/``        the reference fix: every criterion TRUE, exit 0
                     (satisfiability — no arm is being asked the impossible)
``counter/``         the plausible weak patch at the reported symptom: every
                     THIN criterion TRUE, at least one STANDARD criterion
                     FALSE (this is the separation mechanism, demonstrated)
``counter-strong/``  a fix that satisfies the whole STANDARD oracle and still
                     misses the root cause: at least one STRONG criterion
                     FALSE (the standard->strong contrast has headroom, which
                     the design flags as its most fragile leg)
===================  =========================================================

Plus the bank's own integrity: nine tasks, a resolvable holdout, byte-identical
``original/`` stashes, nested oracle levels that match what the verifiers actually
emit, score breakdowns that add up, and — the ablation-v2 defect class — no gate
command anywhere in this bank or its arms carrying a path that does not exist.

Run directly: ``python tests/test_bank_model_tier_v2.py`` (exit 0 on success).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BANK = REPO / "tasks" / "model-tier-v2"
ARMS = REPO / "scenarios" / "model-tier-v2"
sys.path.insert(0, str(REPO / "src"))

EXPECTED_TASKS = {
    "fix-clamp2",
    "fix-strip-unicode",
    "feature-ndjson-merge",
    "fix-tz-window",
    "fix-decimal-round",
    "fix-quota-rollup",
    "fix-graph-cycle",
    "fix-merge-3way",
    "fix-ledger-replay",
}
HOLDOUT = ["fix-quota-rollup"]
OVERLAYS = ("solution", "counter", "counter-strong")

# Criteria that are part of the standard oracle but are not capability-gated: the
# anchor lives in `thin`, and these two are the v1 contract's hygiene checks.
NON_HARD = {"no_regression", "regression_test_present"}

# Placeholder shapes that mean a command string was never wired to a real path — the
# ablation-v2 defect (a gate command shipped with a literal `/path/to/...` in it,
# handed to the shell verbatim).
PLACEHOLDER_TOKENS = ("/path/to", "path/to/", "<", "TODO", "FIXME", "$(", "%s")


def load_toml(path: Path) -> dict:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def load_bank():
    from fathom.taskbank import load_bank as _load

    return _load(BANK)


def oracles() -> dict:
    return load_toml(BANK / "oracles.toml")["tasks"]


def run_verify(task_id: str, view: Path) -> tuple[dict, int]:
    proc = subprocess.run(
        [sys.executable, str(BANK / task_id / "verify.py"), str(view)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.stdout.strip(), f"{task_id}: verify emitted no JSON; stderr=\n{proc.stderr}"
    return json.loads(proc.stdout), proc.returncode


def graded(task_id: str, overlay: str | None) -> tuple[dict, int]:
    """Run the verifier over the fixture, optionally with *overlay* copied on top."""
    with tempfile.TemporaryDirectory() as td:
        view = Path(td) / "view"
        shutil.copytree(BANK / task_id / "fixtures", view)
        if overlay:
            shutil.copytree(BANK / task_id / overlay, view, dirs_exist_ok=True)
        return run_verify(task_id, view)


class TestBankIntegrity(unittest.TestCase):
    def test_loads_nine_tasks_with_a_resolvable_holdout(self):
        bank = load_bank()
        self.assertEqual(bank.name, "model-tier-v2")
        self.assertEqual(bank.dataset_version, "1")
        self.assertEqual(sorted(t.id for t in bank.tasks), sorted(EXPECTED_TASKS))
        self.assertEqual(bank.holdout, HOLDOUT)

    def test_every_task_declares_at_least_two_hard_criteria(self):
        for task in load_bank().tasks:
            with self.subTest(task=task.id):
                hard = task.verify.get("hard_criteria")
                self.assertIsInstance(hard, list, f"{task.id}: missing hard_criteria")
                self.assertGreaterEqual(len(hard), 2, f"{task.id}: needs >=2 hard criteria")

    def test_the_stash_is_byte_identical_to_the_fixture(self):
        """The regression swap only reintroduces the bug if the stash never drifted."""
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                stash = BANK / task_id / "original"
                fixtures = BANK / task_id / "fixtures"
                modules = sorted(stash.glob("*.py"))
                self.assertEqual(len(modules), 1, f"{task_id}: expected one stashed module")
                twins = [m for m in fixtures.rglob(modules[0].name) if "tests" not in m.parts]
                self.assertEqual(len(twins), 1, f"{task_id}: expected one fixture twin")
                self.assertEqual(
                    modules[0].read_text(encoding="utf-8"),
                    twins[0].read_text(encoding="utf-8"),
                    f"{task_id}: the stashed root-cause module drifted from the fixture",
                )
                for stashed in sorted((stash / "tests").glob("*.py")):
                    twin = fixtures / "tests" / stashed.name
                    self.assertTrue(twin.is_file(), f"{task_id}: missing fixture {stashed.name}")
                    self.assertEqual(
                        stashed.read_text(encoding="utf-8"),
                        twin.read_text(encoding="utf-8"),
                        f"{task_id}: stashed {stashed.name} drifted from the fixture",
                    )

    def test_harness_side_directories_never_reach_the_workspace(self):
        """solution/counter/original sit BESIDE fixtures/, so staging cannot copy them."""
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                fixtures = BANK / task_id / "fixtures"
                for name in ("solution", "counter", "counter-strong", "original"):
                    self.assertTrue((BANK / task_id / name).is_dir(), f"{task_id}: no {name}/")
                    self.assertFalse(
                        list(fixtures.rglob(name)), f"{task_id}: {name}/ leaked into fixtures/"
                    )


class TestOracleLevels(unittest.TestCase):
    def test_levels_are_strictly_nested_and_cover_every_task(self):
        levels = oracles()
        self.assertEqual(sorted(levels), sorted(EXPECTED_TASKS))
        for task_id, spec in levels.items():
            with self.subTest(task=task_id):
                thin, standard, strong = (set(spec[k]) for k in ("thin", "standard", "strong"))
                self.assertTrue(thin < standard, f"{task_id}: thin is not a proper subset")
                self.assertTrue(standard < strong, f"{task_id}: standard is not a proper subset")
                self.assertTrue(spec["independent_check"].strip())

    def test_strong_is_exactly_what_the_verifier_emits(self):
        levels = oracles()
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                criteria, _code = graded(task_id, None)
                self.assertEqual(
                    sorted(criteria),
                    sorted(levels[task_id]["strong"]),
                    f"{task_id}: oracles.toml and verify.py disagree on the criterion set",
                )

    def test_hard_criteria_are_the_capability_gated_slice_of_standard(self):
        levels = oracles()
        for task in load_bank().tasks:
            with self.subTest(task=task.id):
                spec = levels[task.id]
                hard, standard, thin = (
                    set(task.verify["hard_criteria"]),
                    set(spec["standard"]),
                    set(spec["thin"]),
                )
                self.assertTrue(hard <= standard, f"{task.id}: a hard criterion is not standard")
                self.assertFalse(hard & thin, f"{task.id}: a hard criterion is in the thin oracle")
                self.assertFalse(hard & NON_HARD, f"{task.id}: hygiene criterion marked hard")


class TestScores(unittest.TestCase):
    def test_every_task_is_scored_and_the_breakdown_adds_up(self):
        data = load_toml(BANK / "scores.toml")
        scores, breakdown = data["scores"], data["breakdown"]
        self.assertEqual(sorted(scores), sorted(EXPECTED_TASKS))
        for task_id, score in scores.items():
            with self.subTest(task=task_id):
                axes = breakdown[task_id]
                total = sum(
                    axes[k]
                    for k in (
                        "base",
                        "structure",
                        "reasoning",
                        "domain",
                        "context",
                        "output",
                        "adjustments",
                    )
                )
                self.assertEqual(
                    total, score, f"{task_id}: axes sum to {total}, score says {score}"
                )

    def test_the_fifty_five_boundary_is_double_covered(self):
        """The design's hardest spread requirement: a rung either side, within +-5."""
        scores = load_toml(BANK / "scores.toml")["scores"]
        near = sorted(t for t, s in scores.items() if abs(s - 55) <= 5)
        self.assertGreaterEqual(len(near), 2, f"55-edge rungs within +-5: {near}")
        self.assertTrue(any(scores[t] <= 55 for t in near), "no rung below the 55 edge")
        self.assertTrue(any(scores[t] > 55 for t in near), "no rung above the 55 edge")


class TestFixtureLeavesWorkToDo(unittest.TestCase):
    def test_the_buggy_fixture_fails_a_hard_criterion_and_has_no_regression_test(self):
        for task in load_bank().tasks:
            with self.subTest(task=task.id):
                criteria, code = graded(task.id, None)
                self.assertIsInstance(criteria, dict)
                for name in task.verify["hard_criteria"]:
                    self.assertIn(name, criteria, f"{task.id}: {name} not emitted")
                self.assertTrue(
                    any(not criteria[c] for c in task.verify["hard_criteria"]),
                    f"{task.id}: no hard criterion fails on the buggy fixture",
                )
                self.assertFalse(criteria["regression_test_present"])
                self.assertNotEqual(code, 0)


class TestSatisfiability(unittest.TestCase):
    def test_the_reference_solution_satisfies_every_criterion(self):
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                criteria, code = graded(task_id, "solution")
                failed = sorted(k for k, v in criteria.items() if not v)
                self.assertEqual(failed, [], f"{task_id}: reference solution fails {failed}")
                self.assertEqual(code, 0)


class TestViolability(unittest.TestCase):
    def test_the_symptom_patch_passes_thin_and_fails_standard(self):
        levels = oracles()
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                spec = levels[task_id]
                criteria, code = graded(task_id, "counter")
                thin_failed = sorted(c for c in spec["thin"] if not criteria[c])
                self.assertEqual(thin_failed, [], f"{task_id}: counter fails thin {thin_failed}")
                self.assertTrue(
                    any(not criteria[c] for c in spec["standard"]),
                    f"{task_id}: the symptom patch satisfies the whole standard oracle",
                )
                self.assertNotEqual(code, 0)

    def test_the_standard_passing_patch_still_fails_the_strong_oracle(self):
        """The standard->strong contrast has headroom on every task, not just in prose."""
        levels = oracles()
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                spec = levels[task_id]
                criteria, code = graded(task_id, "counter-strong")
                standard_failed = sorted(c for c in spec["standard"] if not criteria[c])
                self.assertEqual(
                    standard_failed,
                    [],
                    f"{task_id}: the counter-strong overlay fails standard {standard_failed}",
                )
                self.assertEqual(code, 0)
                strong_only = set(spec["strong"]) - set(spec["standard"])
                self.assertTrue(
                    any(not criteria[c] for c in strong_only),
                    f"{task_id}: the strong oracle adds nothing this patch cannot satisfy",
                )


class TestGateCommandHygiene(unittest.TestCase):
    """The ablation-v2 defect: a gate command carrying a path that does not exist.

    Scoped to this bank and its arms deliberately. The known-defective sibling arm is
    frozen in a committed ledger — editing its command text would fork its config_hash
    and orphan the trials it already paid for — so this guard binds where it can still
    prevent the defect rather than rewriting history to satisfy itself.
    """

    def _commands(self):
        for task in load_bank().tasks:
            run = task.gate.get("run")
            if run:
                yield f"tasks/model-tier-v2/{task.id} [gate].run", str(run)
        for arm_path in sorted(ARMS.glob("*.toml")):
            gate = load_toml(arm_path).get("gate", {})
            for extra in gate.get("extra", []):
                yield f"{arm_path.name} [gate].extra", str(extra)

    def test_no_gate_command_carries_a_placeholder_path(self):
        for where, command in self._commands():
            with self.subTest(command=where):
                for token in PLACEHOLDER_TOKENS:
                    self.assertNotIn(
                        token,
                        command,
                        f"{where}: {command!r} contains the placeholder {token!r}; the "
                        "strategy hands this string to the shell verbatim",
                    )

    def test_every_path_a_gate_command_names_exists(self):
        for where, command in self._commands():
            for token in command.split():
                if "/" not in token and "\\" not in token:
                    continue
                with self.subTest(command=where, path=token):
                    candidate = token.strip("\"'")
                    self.assertTrue(
                        (REPO / candidate).exists() or Path(candidate).exists(),
                        f"{where}: {candidate!r} does not exist from the run's working dir",
                    )

    def test_every_task_gate_actually_runs_on_the_staged_fixture(self):
        """The check that binds: run each command where the strategy would run it.

        String hygiene is necessary and not sufficient — a command with no placeholder
        in it can still be unrunnable. The staged fixture is the working directory a
        gated strategy would use, so a command that cannot execute there (127 / 9009,
        "command not found") fails here rather than after the spend.
        """
        for task in load_bank().tasks:
            command = task.gate.get("run")
            with self.subTest(task=task.id), tempfile.TemporaryDirectory() as td:
                workspace = Path(td) / "view"
                shutil.copytree(BANK / task.id / "fixtures", workspace)
                proc = subprocess.run(  # noqa: S602 - the command is bank-authored
                    command,
                    shell=True,
                    cwd=str(workspace),
                    capture_output=True,
                    text=True,
                    timeout=120,
                    errors="replace",
                )
                self.assertNotIn(
                    proc.returncode,
                    (127, 9009),
                    f"{task.id}: {command!r} could not be executed at all — a gated arm's "
                    f"gate would be meaningless: {(proc.stdout + proc.stderr)[-400:]}",
                )
                self.assertEqual(
                    proc.returncode,
                    0,
                    f"{task.id}: the shipped suite must be GREEN on the buggy fixture (it "
                    f"does not cover the planted bug): {(proc.stdout + proc.stderr)[-400:]}",
                )

    def test_the_check_can_actually_fail(self):
        """A guard nobody can trip is a guard that proves nothing."""
        defective = "python /path/to/probe.py"
        self.assertTrue(any(token in defective for token in PLACEHOLDER_TOKENS))


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
