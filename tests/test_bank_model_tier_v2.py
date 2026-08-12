"""Tests for the model-tier-v2 tier-separating bank and its three-level oracles.

Stdlib-runnable. This is the bank's admission evidence, produced **before** any paid
spend: for every task it demonstrates offline, through the real verifier, that the
criteria CAN be met and CAN fail, and that each oracle level bites where it claims to.

Four overlays per task, each copied over a fresh copy of ``fixtures/``:

===================  =========================================================
``fixtures/`` alone  the buggy starting state: EVERY hard criterion is FALSE,
                     so none of them is a regression guard that is already
                     satisfied before the arm does anything
``solution/``        the reference fix: every criterion TRUE, exit 0
                     (satisfiability — no arm is being asked the impossible)
``counter/``         the plausible weak patch at the reported symptom: every
                     THIN criterion TRUE, every HARD criterion FALSE (this is
                     the separation mechanism, demonstrated)
``counter-strong/``  a fix that satisfies the whole STANDARD oracle and still
                     misses the root cause: at least one STRONG criterion
                     FALSE (the standard->strong contrast has headroom, which
                     the design flags as its most fragile leg)
===================  =========================================================

The counter's HARD row is the one that was missing. The first authoring asserted
only that the counter failed SOME standard criterion, which five tasks satisfied
while still handing the symptom patch a hard criterion for free.
``TestHardCriteriaDerivation`` re-derives the hard set from the overlays and compares
it to what each ``task.toml`` declares, so the decision statistic cannot silently
drift back, and ``TestOverlaysAreDeterminatePerTrial`` pins where each overlay lands
under the per-trial estimator (ADR-0009) that the cells are actually scored with.

Plus the bank's own integrity: ten tasks (nine ladder rungs and one positive
control), a resolvable holdout, byte-identical ``original/`` stashes, nested oracle
levels that match what the verifiers actually emit, score breakdowns that add up,
screen arms that resolve to the matrix arms' own ``config_hash`` so a screen is not
paid for twice, and — the ablation-v2 defect class — no gate command anywhere in
this bank or its arms carrying a path that does not exist.

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
SCREEN_ARMS = REPO / "scenarios" / "model-tier-v2-screen"
sys.path.insert(0, str(REPO / "src"))

# The nine displaced-cause rungs the bank opened with: all of them bug fixes.
BUGFIX_TASKS = {
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
# The shape-extension rungs. Real routing decisions span authoring, refactoring,
# unlocalised debugging, data work, review and planning, and the rubric scores those
# very differently; a ladder made only of bug fixes cannot say whether the mapping
# transfers off that one distribution. Each of these also sits where the scored rubric
# and the reduced floor+shortcut mechanism route differently, which is the only place
# a mechanism comparison can move.
SHAPE_TASKS = {
    "refactor-dedupe-validators",
    "review-locate-defects",
    "plan-migration-order",
    "debug-cache-staleness",
    "data-reconcile-telemetry",
}
# Two of them produce a DOCUMENT, not a patch, so `regression_test_present` has no
# referent: there is no fix for an added test to cover. They emit `code_unchanged`
# instead — the module must come back byte-identical. The exemption is asserted below
# (TestArtifactTasks), never assumed.
ARTIFACT_TASKS = {"review-locate-defects", "plan-migration-order"}
LADDER_TASKS = BUGFIX_TASKS | SHAPE_TASKS
# The positive control, ported verbatim from model-tier-v1 (see its task.toml). It is
# NOT a ladder rung and is deliberately exempt from three of this bank's shape rules —
# the oracle slice, the counter-strong overlay, and the hard_criteria derivation — all
# for the same reason: retuning it to this bank's shape would void the v1 reading that
# makes it a control. Each exemption is asserted below, so it stays a decision on the
# record rather than a gap in coverage.
CONTROL_TASKS = {"control-nonlocal-parse"}
EXPECTED_TASKS = LADDER_TASKS | CONTROL_TASKS
HOLDOUT = ["fix-quota-rollup"]
OVERLAYS = ("solution", "counter", "counter-strong")

# Criteria that are part of the standard oracle but are not capability-gated: the
# anchor lives in `thin`, and these two are the v1 contract's hygiene checks.
NON_HARD = {"no_regression", "regression_test_present", "code_unchanged"}

# The derivation rule's stop-at count (oracles.toml § HOW hard_criteria IS DERIVED).
# NOT a power target: under per-trial scoring (ADR-0009) a cell is one draw whatever k
# is, so k moves the difficulty of the conjunction, not the resolution. Three is the
# headroom target; two is the floor below which the tier verdict would rest on a single
# verifier assertion. Power comes from repeats — see README.md § Power.
HARD_TARGET = 3

# The pre-registered repeat counts, asserted here so the README's plan and the bank's
# own arithmetic cannot drift apart. SCREEN_REPEATS is the design's Part B screen n;
# MATRIX_REPEATS is the first repeat count at which a noiseless rung is determinate
# under per-trial scoring (2 and 3 are not); CONTROL_REPEATS is where the Fisher rule
# clears 0.9 at the control's own v1 rates.
SCREEN_REPEATS = 5
MATRIX_REPEATS = 5
CONTROL_REPEATS = 10

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


def load_bank_task(task_id: str):  # noqa: ANN201 - a taskbank.Task
    return next(t for t in load_bank().tasks if t.id == task_id)


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


def admissible(task_id: str) -> tuple[list[str], list[str]]:
    """(standard-level, strong-level) criteria admissible as hard, MEASURED.

    The derivation rule of ``oracles.toml``: a criterion is admissible iff, through
    the real verifier, it is FALSE on the untouched fixture, FALSE on ``counter/``,
    and TRUE on ``solution/``. Hygiene criteria and the thin anchor are excluded.
    """
    spec = oracles()[task_id]
    fixt, _ = graded(task_id, None)
    cnt, _ = graded(task_id, "counter")
    sol, _ = graded(task_id, "solution")
    std: list[str] = []
    strong: list[str] = []
    for name in spec["strong"]:
        if name in NON_HARD or name in spec["thin"]:
            continue
        if fixt.get(name) is False and cnt.get(name) is False and sol.get(name) is True:
            (std if name in spec["standard"] else strong).append(name)
    return std, strong


class TestBankIntegrity(unittest.TestCase):
    def test_loads_every_task_with_a_resolvable_holdout(self):
        bank = load_bank()
        self.assertEqual(bank.name, "model-tier-v2")
        # Bumped when the shape-extension rungs landed. No ledger exists for this bank,
        # so the bump invalidates nothing — it is the honest record that the dataset
        # changed, which the resume key requires.
        self.assertEqual(bank.dataset_version, "2")
        self.assertEqual(sorted(t.id for t in bank.tasks), sorted(EXPECTED_TASKS))
        self.assertEqual(bank.holdout, HOLDOUT)

    def test_the_run_set_carries_a_positive_control(self):
        """A null on this bank is only interpretable against a task known to separate.

        model-tier-v1 returned 1/7 on-diagonal three times and could not tell "the
        score does not predict the tier" from "the bank had no headroom" — the two
        license opposite decisions and one of them is a deletion. The control is the
        task that discriminates them, so it must be in the bank AND in the RUN set
        (not sealed as a holdout, or it is not there when the matrix is read).
        """
        bank = load_bank()
        for task_id in sorted(CONTROL_TASKS):
            with self.subTest(task=task_id):
                self.assertIn(task_id, {t.id for t in bank.tasks})
                self.assertNotIn(task_id, bank.holdout, f"{task_id}: control cannot be sealed")

    def test_every_task_declares_at_least_two_hard_criteria(self):
        for task in load_bank().tasks:
            with self.subTest(task=task.id):
                hard = task.verify.get("hard_criteria")
                self.assertIsInstance(hard, list, f"{task.id}: missing hard_criteria")
                self.assertGreaterEqual(len(hard), 2, f"{task.id}: needs >=2 hard criteria")

    def test_every_task_declares_a_genre_and_a_reduced_prediction(self):
        """The mechanism comparison is a function of these two fields, so they bind.

        `genre` is what makes "does the mapping transfer off bug fixes" answerable at
        all; `reduced` is the second mechanism's routing, authored and frozen before
        any spend so it cannot be fitted to the result afterwards.
        """
        data = load_toml(BANK / "scores.toml")
        genre, reduced = data["genre"], data["reduced"]
        self.assertEqual(sorted(genre), sorted(EXPECTED_TASKS))
        self.assertEqual(sorted(reduced), sorted(LADDER_TASKS))
        for task_id, spec in reduced.items():
            with self.subTest(task=task_id):
                self.assertIn(spec["prediction"], ("weak", "mid", "strong"))
                # The reduced mechanism IS floor-plus-shortcuts: a floored task is mid
                # unless a shortcut lifts it, and an unfloored task with no shortcut is
                # weak. Anything else would be a third mechanism wearing its name.
                if spec["shortcut"]:
                    self.assertEqual(spec["prediction"], "strong")
                elif spec["floor_fires"]:
                    self.assertEqual(spec["prediction"], "mid")
                else:
                    self.assertEqual(spec["prediction"], "weak")

    def test_the_bank_covers_more_than_one_task_shape(self):
        """A ladder of one genre cannot say whether the mapping transfers off it."""
        genre = load_toml(BANK / "scores.toml")["genre"]
        rungs = {t: g for t, g in genre.items() if t in LADDER_TASKS}
        self.assertGreaterEqual(len(set(rungs.values())), 5, f"genres present: {rungs}")

    def test_enough_rungs_discord_for_the_sign_test_to_be_able_to_fire(self):
        """The arithmetic that sank the first bank, asserted so it cannot recur.

        On the rungs where the two mechanisms agree, no mechanism comparison can move:
        both route the task the same way and buy the same thing. Only DISCORDANT rungs
        carry the contrast, and an exact one-sided sign test over K of them has a
        smallest attainable p of 2**-K. At K=4 that is 0.0625 — above 0.05, so the test
        could not reach significance however the trials fell. The bank shipped with
        three buyable discordant rungs before the shape extension.
        """
        data = load_toml(BANK / "scores.toml")
        scores, reduced = data["scores"], data["reduced"]

        def points(score: float) -> str:
            return "weak" if score <= 25 else ("mid" if score <= 55 else "strong")

        buyable = LADDER_TASKS - set(HOLDOUT)
        discordant = [t for t in buyable if reduced[t]["prediction"] != points(scores[t])]
        self.assertGreaterEqual(
            len(discordant),
            8,
            f"only {len(discordant)} buyable discordant rungs {sorted(discordant)}; the "
            "sign test tolerates no misses below 8 and cannot reach 0.05 below 5",
        )
        self.assertLessEqual(2 ** -len(discordant), 0.05)

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
                required = ["solution", "counter", "original"]
                if task_id in LADDER_TASKS:
                    required.append("counter-strong")
                for name in required:
                    self.assertTrue((BANK / task_id / name).is_dir(), f"{task_id}: no {name}/")
                for name in ("solution", "counter", "counter-strong", "original"):
                    self.assertFalse(
                        list(fixtures.rglob(name)), f"{task_id}: {name}/ leaked into fixtures/"
                    )


class TestArtifactTasks(unittest.TestCase):
    """The document-producing rungs, and the one criterion they swap.

    `review-locate-defects` and `plan-migration-order` forbid a code change, so
    "did the arm add a test covering what it fixed" has no referent. Asserting the
    swap here is what keeps it an exemption on the record rather than a gap: each of
    them must emit `code_unchanged` and must NOT emit `regression_test_present`, and
    every other task must do the opposite.
    """

    def test_only_the_document_tasks_swap_the_hygiene_criterion(self):
        for task_id in sorted(EXPECTED_TASKS):
            with self.subTest(task=task_id):
                criteria, _ = graded(task_id, None)
                if task_id in ARTIFACT_TASKS:
                    self.assertIn("code_unchanged", criteria)
                    self.assertNotIn("regression_test_present", criteria)
                else:
                    self.assertIn("regression_test_present", criteria)
                    self.assertNotIn("code_unchanged", criteria)

    def test_a_document_task_detects_a_code_change(self):
        """A preservation criterion nobody can trip proves nothing."""
        for task_id in sorted(ARTIFACT_TASKS):
            with self.subTest(task=task_id), tempfile.TemporaryDirectory() as td:
                view = Path(td) / "view"
                shutil.copytree(BANK / task_id / "fixtures", view)
                shutil.copytree(BANK / task_id / "solution", view, dirs_exist_ok=True)
                stashed = next((BANK / task_id / "original").glob("*.py"))
                target = next(p for p in view.rglob(stashed.name) if "tests" not in p.parts)
                target.write_text(
                    target.read_text(encoding="utf-8") + "\n# touched\n", encoding="utf-8"
                )
                criteria, code = run_verify(task_id, view)
                self.assertFalse(criteria["code_unchanged"], f"{task_id}: edit undetected")
                self.assertNotEqual(code, 0)


class TestOracleLevels(unittest.TestCase):
    def test_levels_are_strictly_nested_and_cover_every_task(self):
        levels = oracles()
        self.assertEqual(sorted(levels), sorted(EXPECTED_TASKS))
        for task_id, spec in levels.items():
            with self.subTest(task=task_id):
                thin, standard, strong = (set(spec[k]) for k in ("thin", "standard", "strong"))
                self.assertTrue(spec["independent_check"].strip())
                if task_id in CONTROL_TASKS:
                    # Exemption, asserted rather than assumed: the control carries no
                    # oracle slice, because inventing levels for it would change the
                    # task whose prior reading is the point of having it.
                    self.assertEqual(thin, standard, f"{task_id}: control gained a slice")
                    self.assertEqual(standard, strong, f"{task_id}: control gained a slice")
                    continue
                self.assertTrue(thin < standard, f"{task_id}: thin is not a proper subset")
                self.assertTrue(standard < strong, f"{task_id}: standard is not a proper subset")

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

    def test_hard_criteria_exclude_the_anchor_and_the_hygiene_checks(self):
        levels = oracles()
        for task in load_bank().tasks:
            with self.subTest(task=task.id):
                hard = set(task.verify["hard_criteria"])
                thin = set(levels[task.id]["thin"])
                if task.id not in CONTROL_TASKS:
                    self.assertFalse(hard & thin, f"{task.id}: a hard criterion is in thin")
                self.assertFalse(hard & NON_HARD, f"{task.id}: hygiene criterion marked hard")


class TestOverlaysAreDeterminatePerTrial(unittest.TestCase):
    """The decision statistic's three contracted positions, measured per-trial.

    calibration.py scores a trial as ONE draw — it passes iff EVERY hard criterion is
    true (ADR-0009). The bank's contract with that estimator is three positions, and
    this asserts them through the real verifiers rather than in prose:

        fixture   -> 0   (nothing is banked before the arm does anything)
        counter   -> 0   (the symptom patch cannot reach the bar)
        solution  -> 1   (the bar is reachable)

    The fourth overlay, ``counter-strong``, is asserted here too but is NOT one of the
    three: it belongs to the oracle axis. Under the pooled estimator it landed at
    1/3-2/3 of the hard set on every rung — the CI-overlapping middle that reads
    indeterminate. Per-trial there is no middle, and this test pins which side it lands
    on so the reading cannot drift back into ambiguity unnoticed.
    """

    @staticmethod
    def _passes(task_id: str, overlay: str | None, hard: list[str]) -> tuple[int, int]:
        criteria, _ = graded(task_id, overlay)
        present = [c for c in hard if c in criteria]
        return sum(1 for c in present if criteria[c]), len(present)

    def test_the_three_contracted_overlays_score_zero_zero_one(self):
        for task in load_bank().tasks:
            hard = task.verify["hard_criteria"]
            for overlay, expected in ((None, 0), ("counter", 0), ("solution", 1)):
                with self.subTest(task=task.id, overlay=overlay or "fixture"):
                    n_true, k = self._passes(task.id, overlay, hard)
                    self.assertEqual(k, len(hard), f"{task.id}: a hard criterion is not emitted")
                    self.assertEqual(
                        int(n_true == k),
                        expected,
                        f"{task.id}/{overlay or 'fixture'}: per-trial draw is "
                        f"{int(n_true == k)} ({n_true}/{k}), contract says {expected}",
                    )

    def test_the_counter_strong_overlay_lands_on_one_side_not_in_the_middle(self):
        """Determinate under per-trial scoring, and recorded as a fail on every rung."""
        for task_id in sorted(LADDER_TASKS):
            with self.subTest(task=task_id):
                hard = load_bank_task(task_id).verify["hard_criteria"]
                n_true, k = self._passes(task_id, "counter-strong", hard)
                self.assertLess(
                    n_true,
                    k,
                    f"{task_id}: a standard-passing patch clears the hard bar, so the "
                    "hard set adds nothing over the standard oracle here",
                )


class TestHardCriteriaDerivation(unittest.TestCase):
    """The decision statistic is derived from measurement, and re-derived here.

    calibration.py computes every (arm, task) cell from ``hard_criteria`` ALONE. A
    criterion in that set which the plausible symptom patch already satisfies hands the
    counter a free component of the conjunction, which is how the first authoring
    shipped five diluted cells: its suite only ever asserted that the counter failed
    SOME standard criterion, never that it failed every HARD one. These tests assert
    the property that was missing.
    """

    def test_no_hard_criterion_is_one_the_symptom_patch_already_satisfies(self):
        """The dilution check, stated directly: counter scores 0 on the hard set."""
        for task in load_bank().tasks:
            if task.id in CONTROL_TASKS:
                continue
            with self.subTest(task=task.id):
                criteria, _ = graded(task.id, "counter")
                passed = sorted(c for c in task.verify["hard_criteria"] if criteria[c])
                self.assertEqual(
                    passed,
                    [],
                    f"{task.id}: the symptom patch banks hard criteria {passed}; "
                    "the cell dilutes to 0.5-vs-1.0 and reads indeterminate",
                )

    def test_no_hard_criterion_is_already_true_at_the_starting_state(self):
        """A criterion true on the untouched fixture is a regression guard, not capability."""
        for task in load_bank().tasks:
            with self.subTest(task=task.id):
                criteria, _ = graded(task.id, None)
                free = sorted(c for c in task.verify["hard_criteria"] if criteria[c])
                self.assertEqual(free, [], f"{task.id}: hard criteria already true: {free}")

    def test_the_declared_hard_set_is_exactly_what_the_rule_derives(self):
        """Standard-level admissibles first, then strong-level, stop at three, min two."""
        for task in load_bank().tasks:
            if task.id in CONTROL_TASKS:
                continue
            with self.subTest(task=task.id):
                std, strong = admissible(task.id)
                expected = list(std)
                for name in strong:
                    if len(expected) >= max(2, HARD_TARGET):
                        break
                    expected.append(name)
                self.assertGreaterEqual(
                    len(expected), 2, f"{task.id}: fewer than two admissible criteria exist"
                )
                self.assertEqual(
                    sorted(task.verify["hard_criteria"]),
                    sorted(expected),
                    f"{task.id}: hard_criteria is not what the derivation rule yields",
                )

    def test_the_control_is_exempt_and_keeps_its_v1_bar(self):
        """Retuning the control to this bank's rule would void the reading it exists for."""
        bank = {t.id: t for t in load_bank().tasks}
        v1 = load_toml(REPO / "tasks" / "model-tier-v1" / "fix-nonlocal-parse" / "task.toml")
        for task_id in sorted(CONTROL_TASKS):
            with self.subTest(task=task_id):
                self.assertEqual(
                    bank[task_id].verify["hard_criteria"],
                    v1["verify"]["hard_criteria"],
                    f"{task_id}: hard criteria drifted from the v1 task it ports",
                )
                self.assertEqual(bank[task_id].instruction.strip(), v1["instruction"].strip())


class TestScores(unittest.TestCase):
    def test_every_task_is_scored_and_the_breakdown_adds_up(self):
        data = load_toml(BANK / "scores.toml")
        scores, breakdown = data["scores"], data["breakdown"]
        self.assertEqual(sorted(scores), sorted(EXPECTED_TASKS))
        for task_id, score in scores.items():
            if task_id in CONTROL_TASKS:
                # Exemption, asserted: the control's score is model-tier-v1's recorded
                # FINAL from v1's two-rater process, so there is no single per-axis
                # breakdown to record — one that summed to it would be fabricated.
                prov = data["control_provenance"][task_id]
                self.assertNotIn(task_id, breakdown, f"{task_id}: breakdown was invented")
                self.assertEqual(prov["score_final"], score)
                self.assertEqual(prov["bank"], "model-tier-v1")
                continue
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
                    all(not criteria[c] for c in task.verify["hard_criteria"]),
                    f"{task.id}: a hard criterion is already true on the buggy fixture",
                )
                if task.id in ARTIFACT_TASKS:
                    # No code changes on this task, so the hygiene criterion is the
                    # preservation one and it is TRUE at the starting state.
                    self.assertTrue(criteria["code_unchanged"])
                else:
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
        for task_id in sorted(LADDER_TASKS):
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

    def test_the_controls_consumer_band_aid_fixes_the_reported_case_and_nothing_else(self):
        """The control's violability evidence, in its own shape (it has no oracle slice).

        The band-aid the v1 score rationale names: patch each consumer at its symptom
        site, leave the shared parser alone. Both reported cases come out right and the
        shipped suite stays green, but the tagged line defeats it — which is exactly
        what its two hard criteria check.
        """
        for task_id in sorted(CONTROL_TASKS):
            with self.subTest(task=task_id):
                criteria, code = graded(task_id, "counter")
                hard = load_bank_task(task_id).verify["hard_criteria"]
                self.assertTrue(all(not criteria[c] for c in hard), f"{task_id}: band-aid passes")
                self.assertTrue(criteria["no_regression"], f"{task_id}: band-aid breaks the suite")
                self.assertNotEqual(code, 0)

    def test_the_standard_passing_patch_still_fails_the_strong_oracle(self):
        """The standard->strong contrast has headroom on every task, not just in prose."""
        levels = oracles()
        for task_id in sorted(LADDER_TASKS):
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
        for arm_dir in (ARMS, SCREEN_ARMS):
            for arm_path in sorted(arm_dir.glob("*.toml")):
                gate = load_toml(arm_path).get("gate", {})
                for extra in gate.get("extra", []):
                    yield f"{arm_dir.name}/{arm_path.name} [gate].extra", str(extra)

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


class TestScreenArms(unittest.TestCase):
    """The two-arm directory must reuse the census's ledger buckets, not fork them.

    The resume key is (bank, dataset_version, task_id, config_hash, repeat), and
    ``config_hash`` covers name, model, strategy, effort, tools and limits. If a
    screen arm resolves to a different hash than its matrix twin, every screen trial
    is paid for twice — once in the screen, once again in the matrix that cannot see
    it. So the screen is admissible only while the hashes match.
    """

    def _resolved(self, directory: Path) -> dict:
        from fathom.cli import _load_resolved_scenarios

        return {sc.name: sc for sc in _load_resolved_scenarios(directory)}

    def test_the_pair_arms_resolve_to_the_same_config_hash_as_the_census_arms(self):
        matrix, screen = self._resolved(ARMS), self._resolved(SCREEN_ARMS)
        self.assertEqual(sorted(screen), ["haiku", "opus5"], "the pair is weak-vs-strong")
        self.assertTrue(set(screen) <= set(matrix), "a pair arm is not in the census")
        for name in sorted(screen):
            with self.subTest(arm=name):
                self.assertEqual(
                    screen[name].config_hash,
                    matrix[name].config_hash,
                    f"{name}: screen and matrix arms have forked; screen trials would be "
                    "invisible to the matrix and paid for twice",
                )

    def test_the_pair_omits_the_arm_the_control_rule_does_not_use(self):
        """The control's Fisher rule reads two arms; buying a third would buy nothing."""
        self.assertNotIn("sonnet5", self._resolved(SCREEN_ARMS))

    def test_the_pair_arms_are_the_control_rule_arms(self):
        """The two-arm directory exists to serve the control rule, and only that."""
        control = load_toml(BANK / "scores.toml")["control"]
        self.assertEqual(
            sorted(self._resolved(SCREEN_ARMS)),
            sorted({control["weak_arm"], control["strong_arm"]}),
        )


class TestPreRegistration(unittest.TestCase):
    """The buy plan the README commits to, asserted against the bank rather than read.

    `tranche-plan.toml` supersedes `screen-plan.toml`. The screen admitted a rung only
    if it was neither saturated nor floored, and SATURATED was a drop conditioned on
    the outcome under test: a rung the weak tier aces while the rubric routed it dear
    is the clearest evidence a mechanism over-provisions, and the screen deleted it
    before the analysis could see it. Saturation is now a reading, not a drop.
    """

    def _plan(self) -> dict:
        return load_toml(BANK / "tranche-plan.toml")

    def test_the_superseded_screen_plan_is_gone(self):
        """One buy plan, or the run follows whichever file the operator opened."""
        self.assertFalse((BANK / "screen-plan.toml").exists())
        self.assertEqual(self._plan()["supersedes"], "screen-plan.toml")

    def test_every_buyable_rung_is_bought_by_exactly_one_tranche(self):
        plan = self._plan()
        bought: list[str] = []
        for name, tranche in plan["tranches"].items():
            with self.subTest(tranche=name):
                self.assertNotIn(
                    "control-nonlocal-parse" if name != "t0-instrument" else "",
                    tranche["tasks"],
                    "the control is not a ladder rung",
                )
            bought.extend(t for t in tranche["tasks"] if t not in CONTROL_TASKS)
        self.assertEqual(len(bought), len(set(bought)), f"a rung is bought twice: {bought}")
        self.assertEqual(
            sorted(bought),
            sorted(LADDER_TASKS - set(HOLDOUT)),
            "a buyable rung is in no tranche, or a tranche buys something unbuyable",
        )
        self.assertFalse(set(bought) & set(HOLDOUT), "the sealed holdout may not be bought")

    def test_the_discordant_core_is_exactly_the_rungs_the_mechanisms_split_on(self):
        """Tranche 1 buys the contrast and nothing else, and that is checkable.

        A rung where both mechanisms route the same way cannot move C(points) against
        C(reduced): both buy the same tier and pay the same bill. Spending tranche 1 on
        one would be spending on a cell whose answer is known to be a tie.
        """
        data = load_toml(BANK / "scores.toml")
        scores, reduced = data["scores"], data["reduced"]

        def points(score: float) -> str:
            return "weak" if score <= 25 else ("mid" if score <= 55 else "strong")

        buyable = LADDER_TASKS - set(HOLDOUT)
        discordant = {t for t in buyable if reduced[t]["prediction"] != points(scores[t])}
        core = set(self._plan()["tranches"]["t1-discordant-core"]["tasks"])
        self.assertEqual(sorted(core), sorted(discordant))

    def test_each_tranche_trial_count_matches_its_arms_times_tasks_times_repeats(self):
        plan = self._plan()
        for name, tranche in plan["tranches"].items():
            if not tranche["tasks"]:
                continue  # t3 is filled from the earlier tranches' readings
            with self.subTest(tranche=name):
                arms = tranche.get("arms", plan["arms"])
                self.assertEqual(
                    tranche["trials"],
                    len(arms) * len(tranche["tasks"]) * tranche["repeats"],
                    f"{name}: the trial count does not match arms x tasks x repeats",
                )

    def test_every_tranche_says_what_it_decides_and_when_to_stop(self):
        """A tranche with no stop rule is a tranche that always buys the next one."""
        for name, tranche in self._plan()["tranches"].items():
            with self.subTest(tranche=name):
                self.assertTrue(tranche["decides"].strip())
                self.assertTrue(tranche["stop_rule"].strip())

    def test_no_reading_is_robust_at_the_census_repeat_count(self):
        """The arithmetic behind tranche 3, recomputed rather than quoted.

        A robust reading needs the chosen tier's Wilson lower bound to clear tau. At
        five repeats a PERFECT record does not: 5/5 bounds at 0.566 against tau=0.70.
        Ten does, at 0.722. That is the whole justification for a deepening tranche and
        it is arithmetic, not preference.
        """
        from fathom import calibration as cal

        plan = self._plan()
        tau = plan["rule"]["tau"]
        census, deepen = plan["census_repeats"], plan["deepen_repeats"]
        self.assertLess(cal._wilson(census, census)[0], tau)
        self.assertGreaterEqual(cal._wilson(deepen, deepen)[0], tau)

    def test_a_chunk_is_small_enough_to_outlive_an_access_token(self):
        """Interruption is designed for, not hoped about.

        The host's OAuth token lives about eight hours. A chunk is `chunk_tasks` rungs
        at three arms and `census_repeats` repeats; at the v1 observed ~4 minutes of
        wall-clock per trial it must finish inside that window with room to spare, or a
        chunk that starts on a fresh token dies on it and the operator learns about
        resumability the expensive way.
        """
        plan = self._plan()
        trials = plan["chunk_tasks"] * len(plan["arms"]) * plan["census_repeats"]
        self.assertLessEqual(trials * 4 / 60, 8 / 2, f"{trials} trials is over half a token")

    def test_the_control_is_declared_with_a_rule_that_clears_its_power_bar(self):
        control = load_toml(BANK / "scores.toml")["control"]
        self.assertEqual(sorted(control["task"] for _ in [0]), sorted(CONTROL_TASKS))
        self.assertEqual(control["min_repeats"], CONTROL_REPEATS)
        self.assertEqual(control["alpha"], 0.05)

    def test_the_control_rule_reproduces_at_v1_rates_with_probability_at_least_point_nine(self):
        """The bar the rule was sized against, recomputed rather than quoted.

        Exact enumeration over both arms' binomial draws at the control's own recorded
        model-tier-v1 rates (haiku 2/5 -> 0.4, opus5 5/5 -> 1.0), per-trial scoring. The
        rule that shipped before — disjoint Wilson CIs — is recomputed alongside, which
        is what makes the replacement a measurement and not a preference.
        """
        from math import comb

        from fathom import calibration as cal

        control = load_toml(BANK / "scores.toml")["control"]
        n, alpha = control["min_repeats"], control["alpha"]

        def pmf(k: int, p: float) -> float:
            return comb(n, k) * p**k * (1 - p) ** (n - k)

        p_fisher = p_ci = 0.0
        for k_weak in range(n + 1):
            for k_strong in range(n + 1):
                w = pmf(k_weak, 0.4) * pmf(k_strong, 1.0)
                if not w:
                    continue
                if cal.fisher_one_sided(k_weak, n, k_strong, n) <= alpha:
                    p_fisher += w
                if cal._wilson(k_weak, n)[1] < cal._wilson(k_strong, n)[0]:
                    p_ci += w
        self.assertGreaterEqual(round(p_fisher, 3), 0.9, f"control rule fires at {p_fisher:.3f}")
        self.assertLess(p_ci, 0.9, "the disjoint-CI rule would have cleared the bar after all")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    sys.exit(0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1)
