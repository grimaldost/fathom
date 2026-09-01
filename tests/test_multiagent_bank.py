"""Validity gate for the multiagent-composition bank -- stdlib-runnable.

Everything the pre-registration
(``docs/specs/2026-09-01-multiagent-composition-preregistration.md``) declares as a
bank-validity condition, checked before any spend:

* ``TestProbeDeOverlap`` -- no expression the type probe runs is graded by
  ``verify.py``, as a literal string or after stripping spaces and parentheses. If the
  probe and the oracle shared a case, an arm whose gate runs the probe could reach the
  primary endpoint, and the endpoint would no longer be held out.
* ``TestSolutionPassesHeldOut`` -- the reference solution satisfies all six ``held_out``
  criteria, so ``held_out_clean`` is satisfiable and a null is a real null.
* ``TestEscapePassesVisibleSuiteAndFailsHeldOut`` -- the escape (the reference solution
  with ``and not isinstance(v, bool)`` deleted from its numeric guard) passes the whole
  visible suite, fails ``type_bool_arith_heldout``, and reddens the probe. This is the
  defect-escape the bank exists to measure: the visible suite cannot see it, the
  held-out oracle can, and an independent check can too.
* ``TestPlaceboFiresExactlyOnce`` -- the placebo reds on its first call for a fresh
  workspace and greens thereafter.
* ``TestBriefsDifferInOneBlock`` -- the three orchestrator briefs are identical outside
  a single contiguous after-each-PR block. An arm difference anywhere else would be an
  unregistered co-treatment.
* ``TestArmsAreByteIdenticalOutsideTheTreatment`` -- the eight scenarios agree on
  orchestrator model, effort, tool allow-list, limits and ``[env]`` keys.

Run directly: ``python tests/test_multiagent_bank.py`` (exit 0 on success).
"""

import ast
import difflib
import importlib.util
import json
import random
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TASK_DIR = REPO / "tasks" / "multiagent-composition" / "exprlang"
SCENARIO_DIR = REPO / "scenarios" / "multiagent-composition"
ASSET_DIR = SCENARIO_DIR / "assets"

VISIBLE_SUITE = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."]

# The one edit that turns the reference solution into the escape: the explicit
# exclusion of bool from "is this a number?".
ESCAPE_EDIT = " and not isinstance(v, bool)"

HELD_OUT = (
    "type_bool_arith_heldout",
    "type_compare_heldout",
    "env_bool_typing",
    "not_precedence_heldout",
    "error_type_is_typemismatch",
    "short_circuit_heldout",
)

BRIEFS = ("brief-control.md", "brief-placebo.md", "brief-treatment-perpr.md")
BLOCK_START = "## Step 3 — verify, then move on"
BLOCK_END = "## Step 4 — integrate and finish"

ARMS = (
    "control-haiku",
    "control-sonnet",
    "placebo-haiku",
    "placebo-sonnet",
    "perpr-haiku",
    "perpr-sonnet",
    "final-haiku",
    "final-sonnet",
)


def _load(name, path):
    """Import a bank script by path (they are scripts, not an installed package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _normalize(expr):
    """An expression's shape ignoring spaces and parentheses."""
    return expr.replace(" ", "").replace("(", "").replace(")", "")


def _stage(escape=False):
    """A workspace: the fixture with the reference solution overlaid, optionally escaped."""
    tmp = Path(tempfile.mkdtemp(prefix="multiagent-bank-"))
    workspace = tmp / "ws"
    shutil.copytree(TASK_DIR / "fixtures", workspace)
    shutil.copytree(TASK_DIR / "solution", workspace, dirs_exist_ok=True)
    if escape:
        evaluator = workspace / "exprlang" / "evaluator.py"
        text = evaluator.read_text(encoding="utf-8")
        if ESCAPE_EDIT not in text:
            raise AssertionError(f"the escape edit {ESCAPE_EDIT!r} is not in the solution")
        evaluator.write_text(text.replace(ESCAPE_EDIT, ""), encoding="utf-8")
    return tmp, workspace


def _verify(workspace):
    """Run the acceptance verifier over *workspace*; return its criteria dict."""
    proc = subprocess.run(
        [sys.executable, str(TASK_DIR / "verify.py"), str(workspace)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    return json.loads(proc.stdout)


class TestProbeDeOverlap(unittest.TestCase):
    """No probe case is graded by the acceptance oracle."""

    @classmethod
    def setUpClass(cls):
        cls.probe = _load("mc_type_probe", TASK_DIR / "type_probe.py")
        cls.verify = _load("mc_verify", TASK_DIR / "verify.py")
        cls.cases = cls.probe._GROUPS["arith"] + cls.probe._GROUPS["compare"]

    def _graded_literals(self):
        """Every string literal in verify.py -- a deliberate over-approximation."""
        tree = ast.parse((TASK_DIR / "verify.py").read_text(encoding="utf-8"))
        return {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }

    def _graded_generated(self):
        """The expressions the seeded property criterion renders, reproduced exactly."""
        v = self.verify
        rng = random.Random(20260701)
        rendered = set()
        for _ in range(60):
            gen = v._gen_num if rng.random() < 0.5 else v._gen_bool
            rendered.add(v._render(gen(rng, 3)))
        return rendered

    def test_ten_cases(self):
        self.assertEqual(len(self.cases), 10)
        self.assertEqual(len(set(self.cases)), 10)

    def test_no_literal_overlap(self):
        graded = self._graded_literals() | self._graded_generated()
        self.assertEqual(sorted(set(self.cases) & graded), [])

    def test_no_overlap_ignoring_spaces_and_parens(self):
        graded = {_normalize(e) for e in self._graded_literals() | self._graded_generated()}
        collisions = sorted(c for c in self.cases if _normalize(c) in graded)
        self.assertEqual(collisions, [])


class TestSolutionPassesHeldOut(unittest.TestCase):
    """The reference solution satisfies every criterion, held-out group included."""

    def test_solution(self):
        tmp, workspace = _stage()
        try:
            criteria = _verify(workspace)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        for name in HELD_OUT:
            self.assertIn(name, criteria)
            self.assertTrue(criteria[name], f"held_out criterion {name} failed on the solution")
        self.assertTrue(all(criteria.values()), f"solution fails: {criteria}")


class TestEscapePassesVisibleSuiteAndFailsHeldOut(unittest.TestCase):
    """The escape is invisible to the visible suite and visible to the oracle and probe."""

    @classmethod
    def setUpClass(cls):
        cls.tmp, cls.workspace = _stage(escape=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_visible_suite_is_green(self):
        proc = subprocess.run(
            VISIBLE_SUITE,
            cwd=str(self.workspace),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_held_out_arithmetic_criterion_fails(self):
        criteria = _verify(self.workspace)
        self.assertFalse(criteria["type_bool_arith_heldout"])

    def test_probe_reds(self):
        for group in ("arith", "compare"):
            proc = subprocess.run(
                [
                    sys.executable,
                    str(TASK_DIR / "type_probe.py"),
                    str(self.workspace),
                    "--group",
                    group,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
            self.assertEqual(proc.returncode, 1, f"{group}: {proc.stdout}{proc.stderr}")


class TestPlaceboFiresExactlyOnce(unittest.TestCase):
    """Red on the first call for a workspace, green on every later one."""

    def test_red_then_green(self):
        placebo = _load("mc_placebo", TASK_DIR / "placebo_gate.py")
        tmp = Path(tempfile.mkdtemp(prefix="multiagent-placebo-"))
        marker = placebo.marker_path(tmp)
        marker.unlink(missing_ok=True)
        try:
            codes = [
                subprocess.run(
                    [sys.executable, str(TASK_DIR / "placebo_gate.py"), str(tmp)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=60,
                ).returncode
                for _ in range(3)
            ]
        finally:
            marker.unlink(missing_ok=True)
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(codes, [1, 0, 0])


class TestBriefsDifferInOneBlock(unittest.TestCase):
    """The three briefs are identical outside one contiguous after-each-PR block."""

    @classmethod
    def setUpClass(cls):
        cls.lines = {b: (ASSET_DIR / b).read_text(encoding="utf-8").splitlines() for b in BRIEFS}

    def _bounds(self, brief):
        lines = self.lines[brief]
        return lines.index(BLOCK_START), lines.index(BLOCK_END)

    def test_head_and_tail_are_identical(self):
        heads, tails = set(), set()
        for brief in BRIEFS:
            start, end = self._bounds(brief)
            heads.add("\n".join(self.lines[brief][:start]))
            tails.add("\n".join(self.lines[brief][end:]))
        self.assertEqual(len(heads), 1, "briefs differ before the after-each-PR block")
        self.assertEqual(len(tails), 1, "briefs differ after the after-each-PR block")

    def test_every_difference_lies_inside_that_block(self):
        for i, a in enumerate(BRIEFS):
            for b in BRIEFS[i + 1 :]:
                start_a, end_a = self._bounds(a)
                start_b, end_b = self._bounds(b)
                self.assertEqual(start_a, start_b)
                opcodes = difflib.SequenceMatcher(None, self.lines[a], self.lines[b]).get_opcodes()
                changed = [op for op in opcodes if op[0] != "equal"]
                self.assertTrue(changed, f"{a} and {b} are identical")
                for _, i1, i2, j1, j2 in changed:
                    self.assertGreaterEqual(i1, start_a, f"{a} vs {b}: change above the block")
                    self.assertLessEqual(i2, end_a, f"{a} vs {b}: change below the block")
                    self.assertGreaterEqual(j1, start_b, f"{a} vs {b}: change above the block")
                    self.assertLessEqual(j2, end_b, f"{a} vs {b}: change below the block")


class TestArmsAreByteIdenticalOutsideTheTreatment(unittest.TestCase):
    """Orchestrator, tools, limits and [env] keys are the same in all eight arms."""

    @classmethod
    def setUpClass(cls):
        cls.arms = {}
        for arm in ARMS:
            with (SCENARIO_DIR / f"{arm}.toml").open("rb") as fh:
                cls.arms[arm] = tomllib.load(fh)

    def test_all_eight_exist_and_are_named_after_their_file(self):
        self.assertEqual(sorted(cls_name for cls_name in self.arms), sorted(ARMS))
        for arm, data in self.arms.items():
            self.assertEqual(data["name"], arm)

    def test_orchestrator_is_fixed(self):
        for arm, data in self.arms.items():
            self.assertEqual(data["adapter"], "claude-cli", arm)
            self.assertEqual(data["model"], "claude-sonnet-5", arm)
            self.assertEqual(data["effort"], "high", arm)
            self.assertEqual(data["limits"]["trial_timeout_s"], 5400, arm)

    def test_tool_allow_list_is_identical(self):
        allow = {tuple(data["tools"]["allowed"]) for data in self.arms.values()}
        self.assertEqual(len(allow), 1)
        self.assertEqual(
            sorted(allow.pop()),
            sorted(["Read", "Write", "Edit", "Glob", "Grep", "Task", "Bash(python:*)"]),
        )

    def test_env_keys_are_identical_and_templated(self):
        keys = {tuple(sorted(data["env"])) for data in self.arms.values()}
        self.assertEqual(len(keys), 1)
        self.assertEqual(
            list(keys.pop()),
            [
                "CONVOY_GATE_DRIVER",
                "FATHOM_IMPL_MODEL",
                "FATHOM_PLACEBO_GATE",
                "FATHOM_TASK_DIR",
            ],
        )
        for arm, data in self.arms.items():
            # The template, never a resolved path: it is what enters config_hash.
            self.assertEqual(data["env"]["FATHOM_TASK_DIR"], "${FATHOM_TASK_DIR}", arm)
            self.assertTrue(data["env"]["CONVOY_GATE_DRIVER"].startswith("${FATHOM_TASK_DIR}"), arm)
            self.assertTrue(
                data["env"]["FATHOM_PLACEBO_GATE"].startswith("${FATHOM_TASK_DIR}"), arm
            )
            expected = "claude-haiku-4-5" if arm.endswith("-haiku") else "claude-sonnet-5"
            self.assertEqual(data["env"]["FATHOM_IMPL_MODEL"], expected, arm)

    def test_only_the_final_arms_carry_a_harness_gate(self):
        for arm, data in self.arms.items():
            if arm.startswith("final-"):
                self.assertEqual(data["strategy"], "gated-session", arm)
                self.assertEqual(len(data["gate"]["extra"]), 1, arm)
                self.assertIn("run_convoy_gate.py", data["gate"]["extra"][0], arm)
            else:
                self.assertEqual(data["strategy"], "single-session", arm)
                self.assertNotIn("gate", data, arm)

    def test_each_arm_injects_its_own_brief(self):
        expected = {
            "control": "assets/brief-control.md",
            "placebo": "assets/brief-placebo.md",
            "perpr": "assets/brief-treatment-perpr.md",
            # T-final reuses the control brief: its treatment is outside the agent.
            "final": "assets/brief-control.md",
        }
        for arm, data in self.arms.items():
            self.assertEqual(data["context"]["inject"], expected[arm.rsplit("-", 1)[0]], arm)


if __name__ == "__main__":
    unittest.main()
