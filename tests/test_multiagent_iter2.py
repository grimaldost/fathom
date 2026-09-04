"""Validity gate for the iteration-2 arms of the multiagent-composition-v2 bank -- stdlib-runnable.

Iteration 2 (``scenarios/multiagent-composition-v2-iter2/``) buys eight NEW contemporaneous
cells -- control2, placebo2, perpr2, hook2, each in the haiku and sonnet tier-sets -- on the
SAME bank and fixture iteration 1 measured (bank ``multiagent-composition-v2``, ledger
``ledger/multiagent-composition-v2.jsonl``). The 2026-09-03 blind review of iteration 1
named the threats the new cells close: a placebo that matched the gate's reds but neither
its repair actor nor its brief's content; a tool allow-list the platform did not enforce;
two gate mechanisms measured against two convoy releases. This file is what makes the
closing checkable before any spend:

* ``TestAssetsAreIteration1sByteForByte`` -- the control, perpr and hook briefs and the two
  hook assets are iteration 1's, byte for byte; ``brief-placebo2.md`` is ``brief-perpr2.md``
  with exactly two lines substituted (the gate command and the variable that names it) and
  keeps the perpr brief's gate claim, envelope reading and fresh fix-subagent dispatch.
* ``TestArmsAreControl2OutsideTheDocumentedDifferences`` -- all eight TOMLs parse through
  ``fathom.scenario``; orchestrator, effort, ``[tools]`` (allow-list and registry-level
  enforcement) and limits are identical; the ``[env]`` block is identical in keys and
  values except ``FATHOM_IMPL_MODEL``; hook2 adds exactly its three keys and ``[settings]``.
* ``TestPlaceboGate2Envelope`` -- the envelope-form placebo reds once per workspace with a
  ``repair_brief`` carrying the stream-facts marker and naming no type, check or rule,
  then greens.
* ``TestHookGateSpecIsTheDriversComposition`` -- ``hook-gate.toml``'s checks are
  ``series.toml``'s ``[[checks]]`` plus the two probes, exactly as ``run_convoy_gate.py``
  composes them for perpr2.
* ``TestBankMaterialIsUntouched`` -- the fixture fingerprint every iteration-1 ledger row
  carries, the verifier hash the iteration-1 record attests, and the five prompts' hashes.
* ``TestDriverPinIsOverridable`` -- ``run_convoy_gate.py`` keeps its default pin, honours
  ``FATHOM_CONVOY_PIN``, echoes the effective pin, and differs from v1's driver only in the
  pin lines.

Run directly: ``python tests/test_multiagent_iter2.py`` (exit 0 on success).
"""

import contextlib
import difflib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from fathom.scenario import load_scenario  # noqa: E402
from fathom.taskbank import fixture_fingerprint, load_bank  # noqa: E402

BANK_DIR = REPO / "tasks" / "multiagent-composition-v2"
TASK_DIR = BANK_DIR / "exprlang"
V1_TASK_DIR = REPO / "tasks" / "multiagent-composition" / "exprlang"
ITER1 = REPO / "scenarios" / "multiagent-composition-v2"
ITER1_HOOK = REPO / "scenarios" / "multiagent-composition-v2-hook"
ITER2 = REPO / "scenarios" / "multiagent-composition-v2-iter2"
ASSETS = ITER2 / "assets"
LEDGER = REPO / "ledger" / "multiagent-composition-v2.jsonl"
RECORD = REPO / "experiments" / "multiagent-composition-v2" / "record.yaml"
ITER2_RECORD = REPO / "experiments" / "multiagent-composition-v2-iter2" / "record.yaml"

KINDS = ("control2", "placebo2", "perpr2", "hook2")
TIERS = {"haiku": "claude-haiku-4-5", "sonnet": "claude-sonnet-5"}
ARMS = tuple(f"{kind}-{tier}" for kind in KINDS for tier in TIERS)

# Iteration-2 asset -> the iteration-1 file it must equal byte for byte.
COPIED = {
    "brief-control2.md": ITER1 / "assets" / "brief-control.md",
    "brief-perpr2.md": ITER1 / "assets" / "brief-treatment-perpr.md",
    "brief-hook2.md": ITER1_HOOK / "assets" / "brief-hook.md",
    "hook-gate.toml": ITER1_HOOK / "assets" / "hook-gate.toml",
    "hook-settings.json": ITER1_HOOK / "assets" / "hook-settings.json",
}

# The two lines -- and only these -- on which brief-placebo2.md departs from brief-perpr2.md.
PERPR_LINES = (
    "variable `CONVOY_GATE_DRIVER`; run it from the project root, passing this PR's phase tag",
    'python "$CONVOY_GATE_DRIVER" "$FATHOM_TASK_DIR" . --phase <phase tag> --json',
)
PLACEBO_LINES = (
    "variable `FATHOM_PLACEBO_GATE`; run it from the project root, passing this PR's phase tag",
    'python "$FATHOM_PLACEBO_GATE" . --phase <phase tag> --json',
)
# What the placebo brief must keep from the perpr brief: the gate claim, the envelope
# reading, the fresh fix-subagent dispatch. This is the equal-content property.
KEPT_IN_PLACEBO = (
    "The gate's checks are the project's own suite plus two type-contract checks supplied with",
    "the task; a red is a real defect in the implementation, not a problem with the gate.",
    "It prints one JSON object on stdout. Read its `outcome` field.",
    "- `completed` — the gate is green. Move on to the next PR.",
    "envelope's `repair_brief` field and dispatch a **fix subagent** with the Task tool, with",
    "`model` set to `FATHOM_IMPL_MODEL` and that `repair_brief` text pasted **verbatim** as the",
)

ALLOWED = ["Read", "Write", "Edit", "Glob", "Grep", "Task", "Bash(python:*)"]
CONVOY_PIN = "git+https://github.com/grimaldost/convoy@v0.12.0"
DRIVER_DEFAULT_PIN = "git+https://github.com/grimaldost/convoy@v0.11.0"

# [env] shared by all eight arms; FATHOM_IMPL_MODEL is the tier-set and varies by design.
COMMON_ENV = {
    "CONVOY_GATE_DRIVER": "${FATHOM_TASK_DIR}/run_convoy_gate.py",
    "FATHOM_CONVOY_PIN": CONVOY_PIN,
    "FATHOM_PLACEBO_GATE": "${FATHOM_TASK_DIR}/placebo_gate2.py",
    "FATHOM_PROMPTS_DIR": "${FATHOM_PROMPTS_DIR}",
    "FATHOM_TASK_DIR": "${FATHOM_TASK_DIR}",
}
HOOK_ENV = {
    "CONVOY_GATE_SPEC": "${FATHOM_TASK_DIR}/hook-gate.toml",
    "CONVOY_ORACLES": "${FATHOM_TASK_DIR}",
    "CONVOY_TRUSTED_ROOTS": "${workspace}",
}
TOP_LEVEL_KEYS = {
    "name",
    "adapter",
    "model",
    "strategy",
    "effort",
    "tools",
    "context",
    "env",
    "limits",
}

PLACEBO_MARKER = "transient check failed"  # tools/stream_facts.py PLACEBO_RED
FORBIDDEN_IN_REPAIR_BRIEF = ("type", "bool", "boolean", "TypeMismatch", "arithmetic", "comparison")

# Attested by the iteration-1 record (experiments/multiagent-composition-v2/record.yaml) for
# every outcome's verifier, and carried as `fixture_sha` by every iteration-1 ledger row.
VERIFY_SHA = "78d0e86ddeead4fa3da1188d9bd34550590a0fda892dc607891f7853cd8fe241"
FIXTURE_SHA = "9fed6ae4cf452d8ea70a5e27b59531ac7f55438e27784e2cb050802f8876e586"
PROMPT_SHAS = {
    "01-boolean-values.md": "2375a268c468514b9d9690034161a1292d55d393820b3d0bc8b8486b1e923c1c",
    "02-comparison-operators.md": "d3471bbb268fc51cbae420d8db2b7ca0664bbdb80bd3c50f8547aaca34c979ff",
    "03-and-or-short-circuit.md": "efbc32e57791ba4c11695b0994f60aa353f3e5a7f854dde403bf378f53b37402",
    "04-not-operator.md": "8f78a1a0cdafee4424a6fad16c961629ae8de3b34740ae4e1ce803b861635e60",
    "05-conformance-pass.md": "9a62e48a0b9db1ff633f0affdd5e16d77276f3d86a0f215c0a63859801026d9c",
}


def _load(name, path):
    """Import a bank or asset script by path (they are scripts, not an installed package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _raw(arm):
    with (ITER2 / f"{arm}.toml").open("rb") as fh:
        return tomllib.load(fh)


class TestAssetsAreIteration1sByteForByte(unittest.TestCase):
    """The copied assets are iteration 1's; the placebo brief is perpr's with two lines swapped."""

    def test_copied_assets_are_byte_identical(self):
        for name, source in COPIED.items():
            self.assertEqual(
                (ASSETS / name).read_bytes(), source.read_bytes(), f"{name} differs from {source}"
            )

    def test_assets_dir_holds_exactly_the_declared_files(self):
        """Files only: importing placebo_gate2.py by path leaves a __pycache__ behind."""
        expected = sorted([*COPIED, "brief-placebo2.md", "placebo_gate2.py"])
        self.assertEqual(sorted(p.name for p in ASSETS.iterdir() if p.is_file()), expected)

    def test_placebo_brief_differs_from_perpr_in_exactly_two_lines(self):
        perpr = (ASSETS / "brief-perpr2.md").read_text(encoding="utf-8").splitlines()
        placebo = (ASSETS / "brief-placebo2.md").read_text(encoding="utf-8").splitlines()
        changed = [
            op
            for op in difflib.SequenceMatcher(None, perpr, placebo).get_opcodes()
            if op[0] != "equal"
        ]
        self.assertEqual(len(changed), 2, changed)
        pairs = []
        for tag, i1, i2, j1, j2 in changed:
            self.assertEqual(tag, "replace", changed)
            self.assertEqual((i2 - i1, j2 - j1), (1, 1), changed)
            pairs.append((perpr[i1], placebo[j1]))
        self.assertEqual(pairs, list(zip(PERPR_LINES, PLACEBO_LINES)))

    def test_placebo_brief_names_the_placebo_and_nothing_of_the_driver(self):
        text = (ASSETS / "brief-placebo2.md").read_text(encoding="utf-8")
        self.assertNotIn("CONVOY_GATE_DRIVER", text)
        self.assertNotIn("FATHOM_TASK_DIR", text)
        self.assertEqual(text.count("FATHOM_PLACEBO_GATE"), 2)

    def test_placebo_brief_keeps_the_gate_claim_envelope_and_fix_subagent(self):
        """Equal content: the placebo arm is told what the perpr arm is told about its gate."""
        text = (ASSETS / "brief-placebo2.md").read_text(encoding="utf-8")
        for sentence in KEPT_IN_PLACEBO:
            self.assertIn(sentence, text, f"placebo brief lost: {sentence!r}")

    def test_hook_brief_is_the_control_brief_plus_the_marker_sentence(self):
        control = (ASSETS / "brief-control2.md").read_text(encoding="utf-8").splitlines()
        hook = (ASSETS / "brief-hook2.md").read_text(encoding="utf-8").splitlines()
        added = [
            line
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, control, hook).get_opcodes()
            if tag != "equal"
            for line in hook[j1:j2]
        ]
        self.assertTrue(any("[convoy-phase: <phase tag>]" in line for line in added), added)
        self.assertNotIn("gate", "\n".join(added).lower())


class TestArmsAreControl2OutsideTheDocumentedDifferences(unittest.TestCase):
    """Eight arms; one orchestrator; one [tools]; one [env] but for the tier-set and hook2's three keys."""

    @classmethod
    def setUpClass(cls):
        cls.raw = {arm: _raw(arm) for arm in ARMS}
        cls.parsed = {arm: load_scenario(ITER2 / f"{arm}.toml") for arm in ARMS}

    def test_the_dir_holds_exactly_the_eight_arms(self):
        self.assertEqual(sorted(p.stem for p in ITER2.glob("*.toml")), sorted(ARMS))
        for arm in ARMS:
            self.assertEqual(self.raw[arm]["name"], arm)
            self.assertEqual(self.parsed[arm].name, arm)

    def test_every_arm_states_what_differs_from_control2(self):
        for arm in ARMS:
            text = (ITER2 / f"{arm}.toml").read_text(encoding="utf-8")
            self.assertIn("Differs from control2", text, arm)

    def test_orchestrator_tools_and_limits_are_identical(self):
        fixed = {
            (sc.adapter, sc.model, sc.strategy, sc.effort, sc.tools, sc.limits, sc.gate, sc.plugins)
            for sc in self.parsed.values()
        }
        self.assertEqual(len(fixed), 1, "arms disagree outside [context]/[settings]/[env]")
        sc = self.parsed["control2-haiku"]
        self.assertEqual(sc.adapter, "claude-cli")
        self.assertEqual(sc.model, "claude-sonnet-5")
        self.assertEqual(sc.strategy, "single-session")
        self.assertEqual(sc.effort, "high")
        self.assertEqual(sc.tools.source, "none")
        self.assertEqual(list(sc.tools.allowed), ALLOWED)
        self.assertEqual(sc.tools.disallowed, ())
        self.assertEqual(sc.limits.trial_timeout_s, 5400)
        self.assertEqual(sc.gate.extra, ())
        self.assertEqual(sc.plugins.mount, ())

    def test_tool_registry_is_the_allow_list_in_every_arm(self):
        """`registry = "allowed"`: the allow-list applied to the tools the spawn registers.

        The raw key is asserted in every TOML; the parsed field is asserted once
        ``fathom.scenario.ToolsConfig`` carries it (until then the loader ignores the key).
        """
        for arm in ARMS:
            self.assertEqual(self.raw[arm]["tools"]["registry"], "allowed", arm)
            self.assertEqual(set(self.raw[arm]["tools"]), {"source", "allowed", "registry"}, arm)
            tools = self.parsed[arm].tools
            if hasattr(tools, "registry"):
                self.assertEqual(tools.registry, "allowed", arm)

    def test_top_level_tables_are_control2s_plus_settings_for_hook2(self):
        for arm in ARMS:
            expected = TOP_LEVEL_KEYS | ({"settings"} if arm.startswith("hook2-") else set())
            self.assertEqual(set(self.raw[arm]), expected, arm)

    def test_each_arm_injects_its_own_brief_and_only_hook2_injects_settings(self):
        for arm in ARMS:
            kind = arm.rsplit("-", 1)[0]
            sc = self.parsed[arm]
            self.assertEqual(sc.context.inject, str((ASSETS / f"brief-{kind}.md").resolve()), arm)
            if kind == "hook2":
                self.assertEqual(
                    sc.settings.inject, str((ASSETS / "hook-settings.json").resolve()), arm
                )
            else:
                self.assertIsNone(sc.settings.inject, arm)

    def test_env_is_identical_but_for_the_tier_set_and_hook2s_three_keys(self):
        for arm in ARMS:
            kind, tier = arm.rsplit("-", 1)
            env = dict(self.raw[arm]["env"])
            self.assertEqual(env.pop("FATHOM_IMPL_MODEL"), TIERS[tier], arm)
            expected = dict(COMMON_ENV)
            if kind == "hook2":
                expected.update(HOOK_ENV)
            self.assertEqual(env, expected, arm)
            # The loader sorts by key; the sorted tuple is what enters config_hash.
            self.assertEqual(
                [k for k, _ in self.parsed[arm].env.vars], sorted([*expected, "FATHOM_IMPL_MODEL"])
            )

    def test_tier_set_pairs_differ_only_in_the_implementer_model(self):
        for kind in KINDS:
            haiku, sonnet = dict(self.raw[f"{kind}-haiku"]), dict(self.raw[f"{kind}-sonnet"])
            for data in (haiku, sonnet):
                data.pop("name")
                data["env"] = {k: v for k, v in data["env"].items() if k != "FATHOM_IMPL_MODEL"}
            self.assertEqual(haiku, sonnet, kind)

    def test_hook_settings_pin_the_release_the_driver_runs(self):
        """perpr2 (driver at $FATHOM_CONVOY_PIN) and hook2 (uvx in the hook) measure one convoy."""
        settings = json.loads((ASSETS / "hook-settings.json").read_text(encoding="utf-8"))
        commands = [
            h["command"]
            for hooks in settings["hooks"].values()
            for entry in hooks
            for h in entry["hooks"]
            if "uvx --from" in h["command"]
        ]
        self.assertGreaterEqual(len(commands), 2)
        for command in commands:
            self.assertIn(CONVOY_PIN, command)


class TestPlaceboGate2Envelope(unittest.TestCase):
    """Red once per workspace with an uninformative repair brief, green afterwards."""

    @classmethod
    def setUpClass(cls):
        cls.placebo = _load("mc_placebo2", ASSETS / "placebo_gate2.py")

    def _call(self, workspace, *extra):
        return subprocess.run(
            [sys.executable, str(ASSETS / "placebo_gate2.py"), str(workspace), *extra],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

    def test_blocked_then_completed(self):
        tmp = Path(tempfile.mkdtemp(prefix="multiagent-placebo2-"))
        marker = self.placebo.marker_path(tmp)
        marker.unlink(missing_ok=True)
        try:
            first = self._call(tmp, "--phase", "bools", "--json")
            second = self._call(tmp, "--phase", "bools", "--json")
            third = self._call(tmp, "--json", "--phase=compare")
        finally:
            marker.unlink(missing_ok=True)
            shutil.rmtree(tmp, ignore_errors=True)

        self.assertEqual(first.returncode, 1, first.stdout + first.stderr)
        lines = [line for line in first.stdout.splitlines() if line.strip()]
        self.assertEqual(len(lines), 1, "stdout must hold exactly one JSON object")
        envelope = json.loads(lines[0])
        self.assertEqual(envelope["ok"], False)
        self.assertEqual(envelope["outcome"], "blocked")
        self.assertNotIn("placebo", envelope)
        brief = envelope["repair_brief"]
        self.assertIn(PLACEBO_MARKER, brief)
        for word in FORBIDDEN_IN_REPAIR_BRIEF:
            self.assertNotIn(word.lower(), brief.lower(), f"repair_brief names {word!r}")
        self.assertNotIn(".py", brief)
        self.assertIn(PLACEBO_MARKER, first.stderr)

        for proc in (second, third):
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            envelope = json.loads(proc.stdout.strip())
            self.assertEqual(envelope["ok"], True)
            self.assertEqual(envelope["outcome"], "completed")
            self.assertNotIn("placebo", envelope)
            self.assertNotIn("repair_brief", envelope)

    def test_marker_is_keyed_by_workspace_and_lives_outside_it(self):
        a, b = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
        try:
            self.assertNotEqual(self.placebo.marker_path(a), self.placebo.marker_path(b))
            self.assertEqual(self.placebo.marker_path(a), self.placebo.marker_path(a / "."))
            self.assertFalse(str(self.placebo.marker_path(a)).startswith(str(a)))
            self.assertNotEqual(
                self.placebo.marker_path(a),
                _load("mc_placebo1", TASK_DIR / "placebo_gate.py").marker_path(a),
            )
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)


class TestHookGateSpecIsTheDriversComposition(unittest.TestCase):
    """hook-gate.toml == series.toml's [[checks]] + the two probes, as build_spec renders them."""

    def test_checks_match_build_spec(self):
        driver = _load("mc_driver_iter2", TASK_DIR / "run_convoy_gate.py")
        with (TASK_DIR / "series.toml").open("rb") as fh:
            series = tomllib.load(fh)
        composed = tomllib.loads(driver.build_spec(series, "${CONVOY_ORACLES}/type_probe.py", "."))
        with (ASSETS / "hook-gate.toml").open("rb") as fh:
            hook = tomllib.load(fh)
        self.assertEqual(set(hook), {"series", "checks"})
        self.assertEqual(hook["series"], composed["series"])
        self.assertEqual(hook["checks"], composed["checks"])
        self.assertEqual(hook["checks"][: len(series["checks"])], series["checks"])
        probes = hook["checks"][len(series["checks"]) :]
        self.assertEqual(
            [c["name"] for c in probes],
            ["type-contract-probe-arithmetic", "type-contract-probe-comparison"],
        )
        for probe in probes:
            self.assertTrue(probe["independent"] and probe["blocking"])
            self.assertEqual(probe["asset"], "${CONVOY_ORACLES}/type_probe.py")


class TestBankMaterialIsUntouched(unittest.TestCase):
    """fixtures/, prompts/ and verify.py are what iteration 1 measured and attested."""

    def test_fixture_fingerprint_is_the_one_every_iteration_1_row_carries(self):
        bank = load_bank(BANK_DIR)
        task = next(t for t in bank.tasks if t.id == "exprlang")
        self.assertEqual(fixture_fingerprint(task), FIXTURE_SHA)
        seen = set()
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if "fixture_sha" in row:
                    seen.add(row["fixture_sha"])
        self.assertEqual(seen, {FIXTURE_SHA}, "the pinned fingerprint is not the ledger's")

    def test_verifier_hash_is_the_one_the_record_attests(self):
        self.assertEqual(_sha256(TASK_DIR / "verify.py"), VERIFY_SHA)
        self.assertIn(VERIFY_SHA, RECORD.read_text(encoding="utf-8"))

    def test_prompts_are_the_five_iteration_1_prompts(self):
        prompts = TASK_DIR / "prompts"
        self.assertEqual(sorted(p.name for p in prompts.iterdir()), sorted(PROMPT_SHAS))
        for name, sha in PROMPT_SHAS.items():
            self.assertEqual(_sha256(prompts / name), sha, name)


class TestDriverPinIsOverridable(unittest.TestCase):
    """run_convoy_gate.py: default pin unchanged, $FATHOM_CONVOY_PIN honoured and echoed."""

    @classmethod
    def setUpClass(cls):
        cls.driver = _load("mc_driver_pin", TASK_DIR / "run_convoy_gate.py")

    def test_default_pin_is_unchanged(self):
        self.assertEqual(self.driver.CONVOY_PIN, DRIVER_DEFAULT_PIN)
        with mock.patch.dict(os.environ, {"FATHOM_CONVOY_PIN": ""}):
            self.assertEqual(self.driver.effective_pin(), DRIVER_DEFAULT_PIN)
        env = {k: v for k, v in os.environ.items() if k != "FATHOM_CONVOY_PIN"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(self.driver.effective_pin(), DRIVER_DEFAULT_PIN)
        with mock.patch.dict(os.environ, {"FATHOM_CONVOY_PIN": f" {CONVOY_PIN} "}):
            self.assertEqual(self.driver.effective_pin(), CONVOY_PIN)

    def _main(self, env):
        """Run the driver's main() with convoy's launch replaced; return (code, stderr, argv)."""
        calls = []

        def fake_run(args, **kwargs):
            calls.append(list(args))
            return subprocess.CompletedProcess(args, 0, stdout='{"ok": true}\n', stderr="")

        workspace = Path(tempfile.mkdtemp(prefix="multiagent-driver-"))
        err, out = io.StringIO(), io.StringIO()
        argv = ["run_convoy_gate.py", str(TASK_DIR), str(workspace), "--phase", "bools", "--json"]
        clean = {
            k: v
            for k, v in os.environ.items()
            if k not in ("FATHOM_CONVOY_PIN", "FATHOM_CONVOY_GATE_LOCAL")
        }
        try:
            with (
                mock.patch.dict(os.environ, {**clean, **env}, clear=True),
                mock.patch.object(self.driver.subprocess, "run", fake_run),
                mock.patch.object(sys, "argv", argv),
                contextlib.redirect_stderr(err),
                contextlib.redirect_stdout(out),
            ):
                code = self.driver.main()
        finally:
            shutil.rmtree(workspace, ignore_errors=True)
        self.assertEqual(len(calls), 1)
        return code, err.getvalue(), calls[0]

    def test_override_is_launched_and_echoed(self):
        code, stderr, argv = self._main({"FATHOM_CONVOY_PIN": CONVOY_PIN})
        self.assertEqual(code, 0)
        self.assertIn(f"convoy gate via: {CONVOY_PIN}\n", stderr)
        self.assertEqual(argv[:4], ["uvx", "--from", CONVOY_PIN, "convoy"])
        self.assertEqual(argv[4], "gate")
        self.assertEqual(argv[-3:], ["--phase", "bools", "--json"])

    def test_default_is_launched_and_echoed_when_unset(self):
        code, stderr, argv = self._main({})
        self.assertEqual(code, 0)
        self.assertIn(f"convoy gate via: {DRIVER_DEFAULT_PIN}\n", stderr)
        self.assertEqual(argv[:4], ["uvx", "--from", DRIVER_DEFAULT_PIN, "convoy"])

    def test_v2_driver_differs_from_v1_only_in_the_pin_lines(self):
        """Every code line the pin change touches names the pin; nothing of v1's is removed."""
        v1 = (V1_TASK_DIR / "run_convoy_gate.py").read_text(encoding="utf-8").splitlines()
        v2 = (TASK_DIR / "run_convoy_gate.py").read_text(encoding="utf-8").splitlines()
        self.assertNotEqual(v1, v2)
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, v1, v2).get_opcodes():
            if tag == "equal":
                continue
            self.assertIn(tag, ("insert", "replace"), f"v2 drops a v1 line: {v1[i1:i2]}")
            for line in v1[i1:i2] + v2[j1:j2]:
                stripped = line.strip()
                if not stripped or stripped.startswith(("#", '"""')):
                    continue
                self.assertIn("pin", stripped.lower(), f"driver change outside the pin: {line!r}")


class TestRecordMatchesTheArms(unittest.TestCase):
    """Binds the frozen design.cells to the eight scenario TOMLs actually run.

    ER-RECON only checks internal arithmetic; nothing else asserts that
    ``design.cells`` in the typed record names the same eight arms as the
    scenario directory that will actually be run.
    """

    @classmethod
    def setUpClass(cls):
        if not ITER2_RECORD.exists():
            raise unittest.SkipTest(f"no iteration-2 record at {ITER2_RECORD}")
        cls.record = yaml.safe_load(ITER2_RECORD.read_text(encoding="utf-8"))

    def test_design_cells_are_the_eight_scenario_names(self):
        cells = {c["name"] for c in self.record["design"]["cells"]}
        toml_names = {p.stem for p in sorted(ITER2.glob("*.toml"))}
        self.assertEqual(cells, toml_names)
        self.assertEqual(cells, set(ARMS))

    def test_every_cell_plans_sixteen(self):
        cells = self.record["design"]["cells"]
        for cell in cells:
            self.assertEqual(cell["planned_n"], 16, cell["name"])
        self.assertEqual(sum(c["planned_n"] for c in cells), 128)

    def test_verifier_hash_matches_the_bank(self):
        verify_hash = hashlib.sha256((TASK_DIR / "verify.py").read_bytes()).hexdigest()
        outcomes = self.record["outcomes"]
        self.assertGreaterEqual(len(outcomes), 1)
        for outcome in outcomes:
            self.assertEqual(outcome["verifier"]["hash"], verify_hash, outcome["name"])


if __name__ == "__main__":
    unittest.main()
