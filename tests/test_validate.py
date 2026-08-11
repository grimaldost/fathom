"""Tests for fathom.validate — the bank-validation triad as a machine check (FATH-B02).

The rule was a paragraph in CONTRIBUTING and it has already failed twice at real
cost: ``ablation-v1`` was quality-null by instrument (greenfield left no regression
surface), and the v3 and v4 harder banks both ceilinged with 0/180 correctness
failures at n=45 — each discovered after the spend, not before it.

The load-bearing property is the first one: **the verifier must FAIL on the
unmodified fixture.**  A bank whose verifier already passes before the agent
touches anything cannot discriminate between arms, so every arm scores 100% and
the run returns a null that reads as "the tool does not help".

Stdlib-only: ``python tests/test_validate.py`` runs without uv.
"""

from __future__ import annotations

import sys
import unittest
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom import validate  # noqa: E402
from fathom.grading.verifier import VerifierResult  # noqa: E402
from fathom.taskbank import Bank, Task  # noqa: E402


def _task(task_id: str, *, gate: dict | None = None, task_dir: Path | None = None) -> Task:
    return Task(
        id=task_id,
        instruction="do it",
        limits={},
        verify={"entry": "verify.py"},
        task_dir=task_dir or Path("/nonexistent") / task_id,
        gate=gate or {},
    )


def _bank(*tasks: Task) -> Bank:
    return Bank(name="b", dataset_version="1", tasks=list(tasks), holdout=[])


@contextmanager
def _stage(task, base_branch):  # noqa: ANN001, ANN201
    yield Path("/staged") / task.id


def _verifier(outcome: str):  # noqa: ANN202
    def _fn(entry, workspace, timeout_s=60):  # noqa: ANN001, ANN202
        return VerifierResult(
            outcome=outcome, criteria={"c": outcome == "pass"}, stdout="", stderr="", exit_code=0
        )

    return _fn


def _run(bank, *, fixture="fail", solution=None, gate_rc=0, has_solution=False):  # noqa: ANN001, ANN202
    """Drive validate_bank with stubbed staging / verification / gate."""
    calls = {"n": 0}

    def verifier(entry, workspace, timeout_s=60):  # noqa: ANN001, ANN202
        # First call per task is the unmodified fixture, second is the solution.
        calls["n"] += 1
        outcome = fixture if calls["n"] % 2 == 1 else (solution or "pass")
        return VerifierResult(
            outcome=outcome, criteria={"c": outcome == "pass"}, stdout="", stderr="", exit_code=0
        )

    return validate.validate_bank(
        bank,
        stage_fn=_stage,
        verifier_fn=verifier if solution is not None or True else _verifier(fixture),
        gate_fn=lambda cmd, ws: (gate_rc, "gate output"),
        overlay_fn=(lambda task, ws: True) if has_solution else (lambda task, ws: False),
    )


class CriteriaAwareDiscriminationTests(unittest.TestCase):
    """Property 1 reads the CRITERIA, not just the verifier's exit code.

    Caught by the first live run of this check against the real banks:
    ``skill-pyeng-v1`` — the reference bank whose scorecard shows the strongest
    discrimination in the corpus (bare 0/2, pyeng-skill 3/3) — was reported as
    non-discriminating, because its verifier gates exit 0 on ``behavior_preserved``
    (trivially true before the agent touches anything) while the modernization
    signal lives in the other five criteria, all of which start false.

    Exit code alone is too coarse. The property that actually matters is: does
    the untouched fixture leave the arm something to do?
    """

    @staticmethod
    def _checks(outcome: str, criteria: dict | None):  # noqa: ANN205
        def verifier(entry, workspace, timeout_s=60):  # noqa: ANN001, ANN202
            return VerifierResult(
                outcome=outcome, criteria=criteria, stdout="", stderr="", exit_code=0
            )

        return validate.validate_bank(
            _bank(_task("t1")),
            stage_fn=_stage,
            verifier_fn=verifier,
            gate_fn=lambda cmd, ws: (0, ""),
            overlay_fn=lambda task, ws: False,
        )

    def test_exit_zero_with_a_false_criterion_still_discriminates(self) -> None:
        checks = self._checks(
            "pass",
            {
                "behavior_preserved": True,
                "uv": False,
                "src-layout": False,
            },
        )
        first = [c for c in checks if c.prop == validate.PROP_FIXTURE_FAILS]
        self.assertEqual([c.status for c in first], ["pass"], [c.detail for c in first])
        self.assertTrue(validate.validation_ok(checks))

    def test_every_criterion_already_true_is_the_real_ceiling_and_FAILS(self) -> None:
        checks = self._checks("pass", {"behavior_preserved": True, "uv": True})
        self.assertFalse(validate.validation_ok(checks))
        self.assertIn("every criterion", " ".join(c.detail for c in checks if c.status == "fail"))

    def test_a_verifier_emitting_no_criteria_FAILS(self) -> None:
        self.assertFalse(validate.validation_ok(self._checks("pass", None)))
        self.assertFalse(validate.validation_ok(self._checks("fail", {})))

    def test_the_report_names_which_criteria_start_false(self) -> None:
        checks = self._checks("pass", {"a": True, "uv": False})
        detail = " ".join(c.detail for c in checks if c.prop == validate.PROP_FIXTURE_FAILS)
        self.assertIn("uv", detail)


class DiscriminationTests(unittest.TestCase):
    """Property 1 — the verifier must FAIL on the unmodified fixture."""

    def test_a_verifier_that_fails_on_the_fixture_passes_the_check(self) -> None:
        checks = _run(_bank(_task("t1")), fixture="fail")
        first = [c for c in checks if c.prop == validate.PROP_FIXTURE_FAILS]
        self.assertEqual([c.status for c in first], ["pass"])

    def test_a_verifier_that_PASSES_on_the_untouched_fixture_FAILS_the_check(self) -> None:
        # The ceiling failure mode: 0/180 correctness failures at n=45, discovered
        # after the spend. This is the check that must have caught it.
        checks = _run(_bank(_task("t1")), fixture="pass")
        self.assertFalse(validate.validation_ok(checks))
        self.assertIn(
            "ALREADY TRUE",
            " ".join(c.detail for c in checks if c.status == "fail"),
        )

    def test_a_crashing_verifier_FAILS_the_check(self) -> None:
        checks = _run(_bank(_task("t1")), fixture="error")
        self.assertFalse(validate.validation_ok(checks))

    def test_one_bad_task_fails_the_whole_bank(self) -> None:
        calls = {"n": 0}

        def verifier(entry, workspace, timeout_s=60):  # noqa: ANN001, ANN202
            calls["n"] += 1
            # t1 discriminates, t2 already passes.
            outcome = "fail" if calls["n"] == 1 else "pass"
            return VerifierResult(outcome=outcome, criteria={}, stdout="", stderr="", exit_code=0)

        checks = validate.validate_bank(
            _bank(_task("t1"), _task("t2")),
            stage_fn=_stage,
            verifier_fn=verifier,
            gate_fn=lambda cmd, ws: (0, ""),
            overlay_fn=lambda task, ws: False,
        )
        self.assertFalse(validate.validation_ok(checks))


class ReferenceSolutionTests(unittest.TestCase):
    """Property 2 — the verifier must PASS on a reference solution."""

    def test_a_solution_that_verifies_passes(self) -> None:
        checks = _run(_bank(_task("t1")), fixture="fail", solution="pass", has_solution=True)
        sol = [c for c in checks if c.prop == validate.PROP_SOLUTION_PASSES]
        self.assertEqual([c.status for c in sol], ["pass"])
        self.assertTrue(validate.validation_ok(checks))

    def test_a_solution_the_verifier_rejects_FAILS(self) -> None:
        # An unsatisfiable verifier: no arm can ever score, so every result is a
        # null manufactured by the instrument.
        checks = _run(_bank(_task("t1")), fixture="fail", solution="fail", has_solution=True)
        self.assertFalse(validate.validation_ok(checks))

    def test_no_reference_solution_is_UNVERIFIABLE_not_a_pass(self) -> None:
        checks = _run(_bank(_task("t1")), fixture="fail", has_solution=False)
        sol = [c for c in checks if c.prop == validate.PROP_SOLUTION_PASSES]
        self.assertEqual([c.status for c in sol], ["unverifiable"])

    def test_unverifiable_does_not_block_by_default_but_does_under_strict(self) -> None:
        checks = _run(_bank(_task("t1")), fixture="fail", has_solution=False)
        self.assertTrue(validate.validation_ok(checks))
        self.assertFalse(validate.validation_ok(checks, strict=True))


class GateTests(unittest.TestCase):
    """Property 3 — the task's own gate must run green on the untouched fixture."""

    def test_a_green_gate_passes(self) -> None:
        checks = _run(_bank(_task("t1", gate={"run": "pytest"})), gate_rc=0)
        gate = [c for c in checks if c.prop == validate.PROP_GATE_RUNNABLE]
        self.assertEqual([c.status for c in gate], ["pass"])

    def test_a_red_gate_WARNS_but_does_not_refuse(self) -> None:
        # ablation-v2's visible suite encodes the target feature, so its baseline is
        # red BY DESIGN and that red is what a gated arm works against. The harness
        # cannot tell a deliberate red from a broken fixture, so refusing would be a
        # false positive — and a gate that cries wolf is one the operator skips.
        checks = _run(_bank(_task("t1", gate={"run": "pytest"})), gate_rc=1)
        gate = [c for c in checks if c.prop == validate.PROP_GATE_RUNNABLE]
        self.assertEqual([c.status for c in gate], [validate.STATUS_WARN])
        self.assertTrue(validate.validation_ok(checks))
        self.assertFalse(validate.validation_ok(checks, strict=True))

    def test_a_gate_command_that_cannot_run_at_all_FAILS(self) -> None:
        # exit 127 means the shell never found the command: the gate is broken,
        # not red, and every gated arm's gate is meaningless.
        checks = _run(_bank(_task("t1", gate={"run": "nosuchtool"})), gate_rc=127)
        self.assertFalse(validate.validation_ok(checks))

    def test_a_task_declaring_no_gate_is_unverifiable_not_failed(self) -> None:
        checks = _run(_bank(_task("t1")))
        gate = [c for c in checks if c.prop == validate.PROP_GATE_RUNNABLE]
        self.assertEqual([c.status for c in gate], ["unverifiable"])
        self.assertTrue(validate.validation_ok(checks))


class RenderingTests(unittest.TestCase):
    def test_render_names_the_failing_task_and_property(self) -> None:
        checks = _run(_bank(_task("broken-task")), fixture="pass")
        text = validate.render_validation("mybank", checks)
        self.assertIn("broken-task", text)
        self.assertIn("FAIL", text)

    def test_render_of_an_all_pass_bank_says_so(self) -> None:
        checks = _run(_bank(_task("t1")), fixture="fail", solution="pass", has_solution=True)
        self.assertIn("PASS", validate.render_validation("mybank", checks))


class EmptyBankTests(unittest.TestCase):
    def test_a_bank_with_no_tasks_is_not_silently_valid(self) -> None:
        checks = validate.validate_bank(
            _bank(),
            stage_fn=_stage,
            verifier_fn=_verifier("fail"),
            gate_fn=lambda cmd, ws: (0, ""),
            overlay_fn=lambda task, ws: False,
        )
        self.assertFalse(validate.validation_ok(checks))


if __name__ == "__main__":
    unittest.main()
