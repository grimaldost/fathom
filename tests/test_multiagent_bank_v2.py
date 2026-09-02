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
  case-insensitively and across line wraps. If one crept back the bank would be v1 under
  a new name. Every phrase must also match v1, so the list cannot go quietly idle.
* ``TestBankIsV1ExceptThePrompts`` -- task.toml (instruction, ``[gate]``, ``[verify]``,
  ``[limits]``), verify.py, type_probe.py, placebo_gate.py, run_convoy_gate.py,
  series.toml, ``fixtures/`` and ``solution/`` are byte-identical to v1's, and the
  prompts directory holds exactly the five ``.md`` files and nothing else.
* ``TestSolutionPassesEveryCriterion`` -- the reference solution still satisfies all 21
  criteria, so the primary endpoint is satisfiable and a null is a real null.
* ``TestBriefsDifferOnlyInThePromptsDirVariable`` -- each v2 brief differs from its v1
  brief only on lines naming ``FATHOM_PROMPTS_DIR`` / ``FATHOM_TASK_DIR``, and each still
  carries the do-not-read sentence that confines the orchestrator to the prompts dir.
* ``TestArmsAddOnlyThePromptsDirEnvKey`` -- the eight arms are the v1 arms with one
  ``[env]`` key added, identical in all eight.

Run directly: ``python tests/test_multiagent_bank_v2.py`` (exit 0 on success).
"""

import difflib
import filecmp
import json
import re
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
# prescribed. Matched case-insensitively against whitespace-collapsed text, so neither a
# re-capitalised restatement nor one that happens to wrap across two lines gets through.
#
# The list has to pin the removals that CREATE the headroom, not only the ones that are
# easy to name. `type_compare_heldout` grades exactly what PR02's "a comparison requires
# TWO NUMERIC (int or float) operands" used to state, and "use PR01's numeric guard"
# would slip back past a list that only knows the hyphenated guard names -- so the bare
# word `guard` and the three operand-type paraphrases are pinned here too.
FORBIDDEN = (
    "reject",
    "wrong type",
    "numeric-operand guard",
    "boolean-operand guard",
    "require NUMERIC",
    "require BOOLEAN",
    "requires a boolean",
    "requires numeric",
    "guard",
    "numeric (int or float)",
    "requires two numeric",
    "numeric operands",
    "boolean operands",
)

# Phrases kept as prospective paraphrase traps: they are absent from v1 too, so the
# per-phrase non-vacuity check below cannot demand a v1 hit for them.
PROSPECTIVE = ("requires numeric",)

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

# v1's Step 1 warned the orchestrator off the task dir's harness files. FATHOM_PROMPTS_DIR
# is a CHILD of that directory, so moving the prompts does not retire the warning -- one
# ".." still reaches the driver, the probes, series.toml and the reference solution, and
# Read/Glob/Grep are unrestricted by path in every arm's tool allow-list. v2 keeps the
# warning, re-anchored so it names no task-dir path.
DO_NOT_READ = "Read nothing outside `FATHOM_PROMPTS_DIR`."

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


def _scannable(path):
    """Lower-cased, whitespace-collapsed text -- a phrase that wraps still matches."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())


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
            text = _scannable(V2_TASK / "prompts" / name)
            for phrase in FORBIDDEN:
                self.assertNotIn(phrase.lower(), text, f"{name} still says {phrase!r}")

    def test_the_v1_prompts_do_state_it(self):
        """The check is not vacuous: the same scan fails on v1."""
        hits = 0
        for name in PROMPTS:
            text = _scannable(V1_TASK / "prompts" / name)
            hits += sum(1 for phrase in FORBIDDEN if phrase.lower() in text)
        self.assertGreater(hits, 0, "the forbidden-phrase list matches nothing in v1")

    def test_every_phrase_earns_its_place(self):
        """Per-phrase non-vacuity: an entry that matched nothing in v1 pins nothing.

        The aggregate check above stays green while an individual entry is a typo, which
        is how ``requires two numeric`` -- the removal ``type_compare_heldout`` grades --
        went unpinned. Only the phrases declared prospective may miss.
        """
        v1 = [_scannable(V1_TASK / "prompts" / name) for name in PROMPTS]
        idle = [
            phrase
            for phrase in FORBIDDEN
            if phrase not in PROSPECTIVE and not any(phrase.lower() in t for t in v1)
        ]
        self.assertEqual(
            idle, [], f"these phrases match nothing in v1, so they pin nothing: {idle}"
        )


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
                # A blank line carries no content. Every other changed line, on either
                # side, must name one of the two variables -- including the re-anchored
                # do-not-read sentence, whose two continuation lines are unchanged from
                # v1 and so never reach this loop.
                if not line.strip():
                    continue
                self.assertTrue(
                    any(token in line for token in PROMPTS_DIR_TOKENS),
                    f"{brief}: changed line outside the prompts-dir swap: {line!r}",
                )

    def test_no_brief_names_a_prompts_path_under_the_task_dir(self):
        """Narrow by design: this is the v1 prompts path, not a task-dir ban.

        ``brief-treatment-perpr.md`` still passes ``$FATHOM_TASK_DIR`` to the gate driver
        -- ``run_convoy_gate.py`` is byte-identical to v1's and takes the task dir as
        ``argv[1]``, so that argument cannot go. What confines the treatment arm is the
        do-not-read sentence asserted below, not the absence of the variable.
        """
        for brief in BRIEFS:
            text = (V2_SCENARIOS / "assets" / brief).read_text(encoding="utf-8")
            self.assertNotIn("FATHOM_TASK_DIR>/prompts", text, brief)
            self.assertIn("FATHOM_PROMPTS_DIR", text, brief)

    def test_every_brief_confines_the_orchestrator_to_the_prompts_dir(self):
        """The prompts dir is a CHILD of the task dir; moving the prompts is not a fence.

        v1 warned the orchestrator off the harness files; v2 keeps the warning, scoped to
        the directory the brief does name. Without it, one ``..`` from the path Step 1
        prints reaches ``solution/`` -- the full reference evaluator.
        """
        for brief in BRIEFS:
            text = (V2_SCENARIOS / "assets" / brief).read_text(encoding="utf-8")
            self.assertIn(DO_NOT_READ, text, f"{brief} lost the do-not-read guard")


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
