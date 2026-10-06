"""Tests for fathom.validate — the bank-validation triad as a machine check.

The load-bearing property is the first one: **the verifier must FAIL on the
unmodified fixture.**  A bank whose verifier already passes before the agent
touches anything cannot discriminate between arms, so every arm scores 100% and
the run returns a null that reads as "the tool does not help". This is discovered
by running the bank, not by static checks, so the gate must be enforced in code.

Stdlib-only: ``python tests/test_validate.py`` runs without uv.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fathom import validate
from fathom.grading.verifier import VerifierResult
from fathom.taskbank import Bank, Task


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
def _stage(task, base_branch):
    yield Path("/staged") / task.id


def _verifier(outcome: str):
    def _fn(entry, workspace, timeout_s=60):
        return VerifierResult(
            outcome=outcome, criteria={"c": outcome == "pass"}, stdout="", stderr="", exit_code=0
        )

    return _fn


def _run(bank, *, fixture="fail", solution=None, gate_rc=0, has_solution=False):
    """Drive validate_bank with stubbed staging / verification / gate."""
    calls = {"n": 0}

    def verifier(entry, workspace, timeout_s=60):
        # First call per task is the unmodified fixture, second is the solution.
        calls["n"] += 1
        outcome = fixture if calls["n"] % 2 == 1 else (solution or "pass")
        return VerifierResult(
            outcome=outcome, criteria={"c": outcome == "pass"}, stdout="", stderr="", exit_code=0
        )

    return validate.validate_bank(
        bank,
        stage_fn=_stage,
        verifier_fn=verifier if True else _verifier(fixture),
        gate_fn=lambda cmd, ws: (gate_rc, "gate output"),
        overlay_fn=(lambda task, ws: True) if has_solution else (lambda task, ws: False),
    )


class CriteriaAwareDiscriminationTests(unittest.TestCase):
    """Property 1 reads the CRITERIA, not just the verifier's exit code.

    Some banks by design gate exit 0 on a preservation criterion (trivially true
    before the agent touches anything) while the discriminating signal lives in
    the other criteria, all of which start false. Exit code alone is too coarse.

    The property that actually matters is: does the untouched fixture leave the
    arm something to do?
    """

    @staticmethod
    def _checks(outcome: str, criteria: dict | None):
        def verifier(entry, workspace, timeout_s=60):
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
        # The ceiling failure mode: a task so easy every arm succeeds, invisible
        # until spend. This is the check that must prevent it.
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

        def verifier(entry, workspace, timeout_s=60):
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
        # A task's baseline can be red BY DESIGN (a gated arm works against that red).
        # The harness cannot tell a deliberate red from a broken fixture, so refusing
        # would be a false positive — and a gate that cries wolf is one the operator skips.
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


class GateEnvironmentTests(unittest.TestCase):
    """The real gate runner hands the gate none of fathom's own state.

    A gate runs the fixture's code, and the same command later runs agent-written code
    in a gated arm; neither should see a variable naming an arm or the data root.
    """

    _DUMP = (
        "import os\n"
        "for k in ('FATHOM_STREAM_TAG', 'FATHOM_STREAM_DIR', 'FATHOM_HOME', 'PWD', 'OLDPWD'):\n"
        "    print(k, '=', os.environ.get(k))\n"
        "print('PATH kept:', bool(os.environ.get('PATH')))\n"
    )

    def test_run_gate_strips_the_harness_variables_and_keeps_path(self) -> None:
        planted = {
            "FATHOM_STREAM_TAG": "bank-x--planted-arm-name--t--r0",
            "FATHOM_STREAM_DIR": "/planted/data-root/.fathom/streams",
            "FATHOM_HOME": "/planted/data-root",
            "PWD": "/planted/data-root",
            "OLDPWD": "/planted/data-root",
        }
        saved = {k: os.environ.get(k) for k in planted}
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            (ws / "gate.py").write_text(self._DUMP, encoding="utf-8")
            os.environ.update(planted)
            try:
                rc, output = validate.run_gate(f'"{sys.executable}" gate.py', ws)
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        self.assertEqual(rc, 0, output)
        self.assertIn("PATH kept: True", output)
        self.assertNotIn("planted-arm-name", output)
        self.assertNotIn("/planted/data-root", output)

    def test_run_gate_withholds_values_naming_the_data_root(self) -> None:
        # `uv run fathom` from a data repository that pins fathom: VIRTUAL_ENV names the
        # data root's .venv, and PATH starts with its scripts directory.
        from fathom.adapters.claude_cli import hidden_from_children

        names_naming = (
            "import os, sys\n"
            "root = sys.argv[1].replace('\\\\', '/').lower()\n"
            "print('NAMING:', sorted(k for k, v in os.environ.items()\n"
            "                        if root in v.replace('\\\\', '/').lower()))\n"
        )
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as w:
            data_root = Path(d) / "data-root"
            scripts = data_root / ".venv" / ("Scripts" if os.name == "nt" else "bin")
            scripts.mkdir(parents=True)
            script = Path(d) / "names.py"
            script.write_text(names_naming, encoding="utf-8")
            planted = {
                "VIRTUAL_ENV": str(data_root / ".venv"),
                "PATH": os.pathsep.join([str(scripts), os.environ.get("PATH", "")]),
            }
            saved = {k: os.environ.get(k) for k in planted}
            os.environ.update(planted)
            try:
                with hidden_from_children(data_root):
                    rc, output = validate.run_gate(
                        f'"{sys.executable}" "{script}" "{data_root.resolve()}"', Path(w)
                    )
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        self.assertEqual(rc, 0, output)
        self.assertIn("NAMING: []", output)

    def test_run_gate_holds_no_billing_or_api_credential(self) -> None:
        # The same environment a gated arm's gate gets, so a gate checked here behaves
        # as it will under a run.
        dump = (
            "import os\n"
            "print('SEEN:', sorted(k for k in os.environ if k.upper() in "
            "{'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'}))\n"
        )
        planted = {"ANTHROPIC_API_KEY": "planted-key", "ANTHROPIC_AUTH_TOKEN": "planted-token"}
        saved = {k: os.environ.get(k) for k in planted}
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d)
            (ws / "gate.py").write_text(dump, encoding="utf-8")
            os.environ.update(planted)
            try:
                rc, output = validate.run_gate(f'"{sys.executable}" gate.py', ws)
            finally:
                for k, v in saved.items():
                    if v is None:
                        os.environ.pop(k, None)
                    else:
                        os.environ[k] = v
        self.assertEqual(rc, 0, output)
        self.assertIn("SEEN: []", output)


class GateTimeoutTests(unittest.TestCase):
    def test_a_gate_that_outlives_its_timeout_is_stopped_with_its_children(self) -> None:
        """A shell's child that sleeps past the timeout neither holds the check until it
        is done nor runs on to write into the staged fixture."""
        import time

        late = (
            f'"{sys.executable}" -c "import time, pathlib; time.sleep(5); '
            "pathlib.Path('late.txt').write_text('x')\" && echo done"
        )
        with (
            mock.patch.object(validate, "_GATE_TIMEOUT_S", 1),
            tempfile.TemporaryDirectory() as d,
        ):
            ws = Path(d)
            start = time.monotonic()
            with self.assertRaises(subprocess.TimeoutExpired):
                validate.run_gate(late, ws)
            elapsed = time.monotonic() - start
            time.sleep(max(0.0, 6.5 - elapsed))
            left = sorted(p.name for p in ws.iterdir())
        self.assertLess(elapsed, 4, f"the gate returned after {elapsed:.1f}s")
        self.assertEqual(left, [])


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
