"""Validity gate for the multiagent-composition-v2 bank -- stdlib-runnable.

v2 is v1 with exactly two changes, pre-registered before any paid trial in
``docs/specs/2026-09-01-multiagent-composition-preregistration.md`` (section
"Pre-registration -- bank v2"): the five PR prompts stop stating the type rule and
prescribing the operand guards, and the briefs point the orchestrator at
``FATHOM_PROMPTS_DIR`` -- a directory holding the prompts and nothing else -- instead of
at the task dir. Everything else is the v1 bank byte for byte, because the endpoint,
the probes, the placebo, the driver and the arms have to stay comparable.

This file is what makes "exactly two changes" checkable:

* ``TestPromptsDoNotStateTheRule`` -- no v2 prompt contains any of the removed phrasings,
  case-insensitively. If one crept back the bank would be v1 under a new name.
* ``TestBankIsV1ExceptThePrompts`` -- task.toml (instruction, ``[gate]``, ``[verify]``,
  ``[limits]``), verify.py, type_probe.py, placebo_gate.py, run_convoy_gate.py,
  series.toml, ``fixtures/`` and ``solution/`` are byte-identical to v1's, and the
  prompts directory holds exactly the five ``.md`` files and nothing else.
* ``TestSolutionPassesEveryCriterion`` -- the reference solution still satisfies all 21
  criteria, so the primary endpoint is satisfiable and a null is a real null.
* ``TestBriefsDifferOnlyInThePromptsDirVariable`` -- each v2 brief differs from its v1
  brief only on lines naming ``FATHOM_PROMPTS_DIR`` / ``FATHOM_TASK_DIR`` (plus the two
  continuation lines of the one sentence removed with them, pinned verbatim below).
* ``TestArmsAddOnlyThePromptsDirEnvKey`` -- the eight arms are the v1 arms with one
  ``[env]`` key added, identical in all eight.

Run directly: ``python tests/test_multiagent_bank_v2.py`` (exit 0 on success).
"""

import difflib
import filecmp
import json
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
V1_TASK = REPO / "tasks" / "multiagent-composition" / "exprlang"
V2_TASK = REPO / "tasks" / "multiagent-composition-v2" / "exprlang"
V1_SCENARIOS = REPO / "scenarios" / "multiagent-composition"
V2_SCENARIOS = REPO / "scenarios" / "multiagent-composition-v2"

PROMPTS = (
    "01-boolean-values.md",
    "02-comparison-operators.md",
    "03-and-or-short-circuit.md",
    "04-not-operator.md",
    "05-conformance-pass.md",
)

# The phrasings the pre-registration removes: the type rule stated, and the guard
# prescribed. Matched case-insensitively, so a re-capitalised restatement still fails.
FORBIDDEN = (
    "reject",
    "wrong type",
    "numeric-operand guard",
    "boolean-operand guard",
    "require NUMERIC",
    "require BOOLEAN",
    "requires a boolean",
    "requires numeric",
)

# Copied wholesale from v1; none of it may drift.
IDENTICAL_FILES = (
    "task.toml",
    "verify.py",
    "type_probe.py",
    "placebo_gate.py",
    "run_convoy_gate.py",
    "series.toml",
)
IDENTICAL_TREES = ("fixtures", "solution")

# 15 `full` criteria + 6 `held_out`.
CRITERION_COUNT = 21

BRIEFS = ("brief-control.md", "brief-placebo.md", "brief-treatment-perpr.md")
PROMPTS_DIR_TOKENS = ("FATHOM_PROMPTS_DIR", "FATHOM_TASK_DIR")

# v1's Step 1 warned the orchestrator off the task dir's harness files. v2 has no
# brief-given path to that directory, so the warning goes; its first line names
# FATHOM_TASK_DIR, and these are the two continuation lines that do not.
REMOVED_CONTINUATION_LINES = (
    "not part of this task; opening them would invalidate the measurement this session is part",
    "of, and they will not help you.",
)

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

EXPECTED_ENV_KEYS = [
    "CONVOY_GATE_DRIVER",
    "FATHOM_IMPL_MODEL",
    "FATHOM_PLACEBO_GATE",
    "FATHOM_PROMPTS_DIR",
    "FATHOM_TASK_DIR",
]


def _tree_diff(left, right):
    """Every path under *left*/*right* that differs, recursively (ignoring caches)."""
    cmp = filecmp.dircmp(str(left), str(right), ignore=["__pycache__"])
    differing = [f"{left.name}/{n}" for n in cmp.left_only + cmp.right_only + cmp.diff_files]
    for name in cmp.common_dirs:
        differing += _tree_diff(left / name, right / name)
    return differing


class TestPromptsDoNotStateTheRule(unittest.TestCase):
    """No v2 prompt states the type rule or prescribes an operand guard."""

    def test_no_forbidden_phrase(self):
        for name in PROMPTS:
            text = (V2_TASK / "prompts" / name).read_text(encoding="utf-8").lower()
            for phrase in FORBIDDEN:
                self.assertNotIn(phrase.lower(), text, f"{name} still says {phrase!r}")

    def test_the_v1_prompts_do_state_it(self):
        """The check is not vacuous: the same scan fails on v1."""
        hits = 0
        for name in PROMPTS:
            text = (V1_TASK / "prompts" / name).read_text(encoding="utf-8").lower()
            hits += sum(1 for phrase in FORBIDDEN if phrase.lower() in text)
        self.assertGreater(hits, 0, "the forbidden-phrase list matches nothing in v1")


class TestBankIsV1ExceptThePrompts(unittest.TestCase):
    """Everything but ``prompts/`` is the v1 bank byte for byte."""

    def test_task_instruction_is_byte_identical(self):
        with (V1_TASK / "task.toml").open("rb") as fh:
            v1 = tomllib.load(fh)
        with (V2_TASK / "task.toml").open("rb") as fh:
            v2 = tomllib.load(fh)
        self.assertEqual(v2["instruction"], v1["instruction"])
        self.assertEqual(v2["gate"], v1["gate"])
        self.assertEqual(v2["verify"], v1["verify"])
        self.assertEqual(v2["limits"], v1["limits"])

    def test_copied_files_are_byte_identical(self):
        for name in IDENTICAL_FILES:
            self.assertEqual(
                (V2_TASK / name).read_bytes(),
                (V1_TASK / name).read_bytes(),
                f"{name} differs from v1",
            )

    def test_copied_trees_are_byte_identical(self):
        for name in IDENTICAL_TREES:
            self.assertEqual(_tree_diff(V1_TASK / name, V2_TASK / name), [])

    def test_prompts_dir_holds_the_five_prompts_and_nothing_else(self):
        entries = sorted(p.name for p in (V2_TASK / "prompts").iterdir())
        self.assertEqual(entries, sorted(PROMPTS))

    def test_bank_is_named_v2_and_keeps_dataset_version_1(self):
        with (V2_TASK.parent / "bank.toml").open("rb") as fh:
            bank = tomllib.load(fh)
        self.assertEqual(bank["name"], "multiagent-composition-v2")
        self.assertEqual(bank["dataset_version"], "1")


class TestSolutionPassesEveryCriterion(unittest.TestCase):
    """The reference solution satisfies all 21 criteria under the v2 bank."""

    def test_solution(self):
        tmp = Path(tempfile.mkdtemp(prefix="multiagent-bank-v2-"))
        try:
            workspace = tmp / "ws"
            shutil.copytree(V2_TASK / "fixtures", workspace)
            shutil.copytree(V2_TASK / "solution", workspace, dirs_exist_ok=True)
            proc = subprocess.run(
                [sys.executable, str(V2_TASK / "verify.py"), str(workspace)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,
            )
            criteria = json.loads(proc.stdout)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.assertEqual(len(criteria), CRITERION_COUNT, sorted(criteria))
        failed = sorted(name for name, ok in criteria.items() if not ok)
        self.assertEqual(failed, [], f"solution fails: {failed}")


class TestBriefsDifferOnlyInThePromptsDirVariable(unittest.TestCase):
    """Each v2 brief is its v1 brief with the prompts-dir variable swapped in."""

    def test_every_changed_line_names_the_variable(self):
        for brief in BRIEFS:
            v1 = (V1_SCENARIOS / "assets" / brief).read_text(encoding="utf-8").splitlines()
            v2 = (V2_SCENARIOS / "assets" / brief).read_text(encoding="utf-8").splitlines()
            self.assertNotEqual(v1, v2, f"{brief} is unchanged")
            opcodes = difflib.SequenceMatcher(None, v1, v2).get_opcodes()
            changed = [
                line
                for tag, i1, i2, j1, j2 in opcodes
                if tag != "equal"
                for line in v1[i1:i2] + v2[j1:j2]
            ]
            for line in changed:
                # A blank line carries no content; the two pinned lines are the tail of
                # the one sentence removed with its FATHOM_TASK_DIR opener.
                if not line.strip() or line.strip() in REMOVED_CONTINUATION_LINES:
                    continue
                self.assertTrue(
                    any(token in line for token in PROMPTS_DIR_TOKENS),
                    f"{brief}: changed line outside the prompts-dir swap: {line!r}",
                )

    def test_no_brief_sends_the_orchestrator_to_the_task_dir_for_prompts(self):
        for brief in BRIEFS:
            text = (V2_SCENARIOS / "assets" / brief).read_text(encoding="utf-8")
            self.assertNotIn("FATHOM_TASK_DIR>/prompts", text, brief)
            self.assertIn("FATHOM_PROMPTS_DIR", text, brief)


class TestArmsAddOnlyThePromptsDirEnvKey(unittest.TestCase):
    """The eight arms are v1's, plus one ``[env]`` key, identical in all eight."""

    @classmethod
    def setUpClass(cls):
        cls.v1, cls.v2 = {}, {}
        for arm in ARMS:
            with (V1_SCENARIOS / f"{arm}.toml").open("rb") as fh:
                cls.v1[arm] = tomllib.load(fh)
            with (V2_SCENARIOS / f"{arm}.toml").open("rb") as fh:
                cls.v2[arm] = tomllib.load(fh)

    def test_arm_names_are_the_v1_names(self):
        self.assertEqual(sorted(self.v2), sorted(ARMS))
        for arm, data in self.v2.items():
            self.assertEqual(data["name"], arm)

    def test_everything_but_env_matches_v1(self):
        for arm in ARMS:
            v1 = {k: v for k, v in self.v1[arm].items() if k != "env"}
            v2 = {k: v for k, v in self.v2[arm].items() if k != "env"}
            self.assertEqual(v2, v1, f"{arm} differs from v1 outside [env]")

    def test_env_keys_are_identical_across_arms_and_add_only_the_prompts_dir(self):
        keys = {tuple(sorted(data["env"])) for data in self.v2.values()}
        self.assertEqual(len(keys), 1, "arms disagree on their [env] keys")
        self.assertEqual(list(keys.pop()), EXPECTED_ENV_KEYS)
        for arm in ARMS:
            env = dict(self.v2[arm]["env"])
            self.assertEqual(env.pop("FATHOM_PROMPTS_DIR"), "${FATHOM_PROMPTS_DIR}", arm)
            self.assertEqual(env, self.v1[arm]["env"], f"{arm} changed an inherited [env] value")


if __name__ == "__main__":
    unittest.main()
