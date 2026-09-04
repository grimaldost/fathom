"""Tests for tools/stream_facts.py — event-level per-trial facts from persisted streams.

Synthetic streams shaped like the live CLI's stream-json (init line, assistant tool_use,
user tool_result, result), a voided predecessor cluster, a fix-spawn cluster, an exposure
read inside a subagent, and a driver call that came back red. Iteration 2 adds a synthetic
hook.log shaped like convoy 0.12.0's ``interface/hook.py`` records and the per-arm arming
verdicts.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import stream_facts as sf  # noqa: E402

BANK = "bank-v2"
TASK = "tasks/bank-v2/exprlang"


def _init(cwd: str) -> dict:
    return {"type": "system", "subtype": "init", "cwd": cwd, "session_id": "s", "tools": ["Bash"]}


def _use(name: str, inp: dict, uid: str, parent: str | None = None) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": parent,
        "message": {
            "model": "claude-haiku-4-5-20251001",
            "content": [{"type": "tool_use", "id": uid, "name": name, "input": inp}],
        },
    }


def _result(uid: str, text: str, is_error: bool = False, parent: str | None = None) -> dict:
    return {
        "type": "user",
        "parent_tool_use_id": parent,
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": uid, "content": text, "is_error": is_error}
            ]
        },
    }


def _write(d: Path, name: str, evs: list[dict], with_result: bool = True) -> Path:
    p = d / name
    lines = [json.dumps(e) for e in evs]
    if with_result:
        lines.append(json.dumps({"type": "result", "subtype": "success"}))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _ledger(d: Path, voided: bool) -> Path:
    rows = []
    base = {"bank": BANK, "dataset_version": "1", "task_id": "exprlang"}
    # perpr-haiku r3: a first (voided) trial, then a void row, then the re-bought trial
    rows.append(
        {
            **base,
            "kind": "trial",
            "scenario": "perpr-haiku",
            "config_hash": "h1",
            "repeat": 3,
            "status": "completed",
            "verifier_results": {},
        }
    )
    if voided:
        rows.append(
            {
                **base,
                "kind": "void",
                "scenario": "perpr-haiku",
                "config_hash": "h1",
                "repeat": 3,
                "voided_at": "2026-09-02T17:09:42Z",
                "reason": "test",
            }
        )
        rows.append(
            {
                **base,
                "kind": "trial",
                "scenario": "perpr-haiku",
                "config_hash": "h1",
                "repeat": 3,
                "status": "completed",
                "verifier_results": {},
            }
        )
    rows.append(
        {
            **base,
            "kind": "trial",
            "scenario": "final-haiku",
            "config_hash": "h2",
            "repeat": 5,
            "status": "completed",
            "verifier_results": {},
        }
    )
    p = d / "ledger.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    return p


# epochs: before the void (17:09:42Z = 1788368982000) and after
BEFORE = 1788360000000
AFTER = 1788370000000


class SurvivingStreamsTests(unittest.TestCase):
    def test_voided_predecessor_is_dropped_and_fix_spawns_stay_with_their_orchestrator(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            ledger = _ledger(d, voided=True)
            old = _write(
                d,
                f"{BANK}--perpr-haiku--exprlang--r3--a1--{BEFORE}.ndjson",
                [_init("C:/stage-old")],
            )
            new = _write(
                d, f"{BANK}--perpr-haiku--exprlang--r3--a1--{AFTER}.ndjson", [_init("C:/stage-new")]
            )
            orch = _write(
                d,
                f"{BANK}--final-haiku--exprlang--r5--a1--{AFTER + 10}.ndjson",
                [_init("C:/stage-f")],
            )
            spawn = _write(
                d,
                f"{BANK}--final-haiku--exprlang--r5--a1--{AFTER + 20}.ndjson",
                [_init("C:/stage-f")],
            )
            got = sf.surviving_streams(ledger, [d])
            self.assertEqual(got[("perpr-haiku", 3)], [new])
            self.assertNotIn(old, got[("perpr-haiku", 3)])
            self.assertEqual(got[("final-haiku", 5)], [orch, spawn])

    def test_untagged_and_uncounted_files_are_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            ledger = _ledger(d, voided=False)
            _write(d, "untagged--a1--123.ndjson", [_init("C:/x")])
            _write(d, f"{BANK}--control-haiku--exprlang--r9--a1--{AFTER}.ndjson", [_init("C:/y")])
            got = sf.surviving_streams(ledger, [d])
            # the counted keys have no stream here; the uncounted and untagged files are not keys
            self.assertEqual(set(got), set())


class TrialFactsTests(unittest.TestCase):
    def test_counts_are_event_level_and_orchestrator_scoped(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            drv = "python C:/harness/run_convoy_gate.py C:/harness . --phase bools --json"
            evs = [
                _init("C:/stage"),
                _use(
                    "Agent",
                    {"prompt": f"brief mentions {sf.DRIVER_MARKER} twice {sf.DRIVER_MARKER}"},
                    "a1",
                ),
                _result("a1", "done"),
                _use("Bash", {"command": drv}, "b1"),
                _result("b1", 'Exit code 1 [RED] probe {"outcome": "blocked"}', is_error=True),
                _use("Bash", {"command": drv}, "b2"),
                _result("b2", '{"outcome": "completed"}'),
                _use("Agent", {"prompt": "fix"}, "a2"),
                _result("a2", "fixed"),
                # a subagent-level dispatch and driver call must not count as the orchestrator's
                _use("Agent", {"prompt": "nested"}, "a3", parent="a2"),
                _use("Bash", {"command": drv}, "b3", parent="a2"),
                _result("b3", '{"outcome": "completed"}', parent="a2"),
                # exposure: a subagent reads the oracle; a Bash driver run is not exposure
                _use("Read", {"file_path": f"C:/repo/{TASK}/verify.py"}, "r1", parent="a1"),
                _use("Read", {"file_path": f"C:/repo/{TASK}/prompts/pr01.md"}, "r2", parent="a1"),
                _use(
                    "Bash",
                    {"command": f"python C:/repo/{TASK}/run_convoy_gate.py C:/repo/{TASK} ."},
                    "b4",
                ),
                _result("b4", '{"outcome": "completed"}'),
            ]
            orch = _write(d, "o.ndjson", evs)
            spawn = _write(
                d,
                "s.ndjson",
                [
                    _init("C:/stage"),
                    _use("Bash", {"command": drv}, "b9"),
                    _result("b9", "[RED]", True),
                ],
            )
            f = sf.trial_facts("perpr-haiku", 3, [orch, spawn], "bank-v2")
            self.assertEqual(f.agent_dispatches, 2)
            self.assertEqual((f.driver_calls, f.driver_reds), (3, 1))
            # b3 ran inside a subagent, b9 inside the fix spawn: neither is the orchestrator's
            self.assertEqual(f.spawn_driver_calls, 2)
            self.assertEqual([(x.tool, x.level) for x in f.exposure], [("Read", "subagent")])
            self.assertIn("verify.py", f.exposure[0].path)
            self.assertEqual(f.models, {"haiku-4-5-20251001"})
            self.assertFalse(f.truncated)

    def test_placebo_red_and_truncated_stream(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            evs = [
                _init("C:/stage"),
                _use("Bash", {"command": "python C:/h/placebo_gate.py ."}, "p1"),
                _result("p1", f"{sf.PLACEBO_RED}: re-run", is_error=True),
                _use("Bash", {"command": "python C:/h/placebo_gate.py ."}, "p2"),
                _result("p2", "ok"),
            ]
            orch = _write(d, "o.ndjson", evs, with_result=False)
            f = sf.trial_facts("placebo-haiku", 1, [orch], "bank-v2")
            self.assertEqual((f.placebo_calls, f.placebo_reds), (2, 1))
            self.assertTrue(f.truncated)

    def test_dose_table_excludes_truncated_trials(self):
        a = sf.TrialFacts("perpr-haiku", 0, [], "o", agent_dispatches=7, driver_reds=1)
        b = sf.TrialFacts("perpr-haiku", 1, [], "o", agent_dispatches=8, driver_reds=2)
        t = sf.TrialFacts("perpr-haiku", 2, [], "o", agent_dispatches=2, truncated=True)
        lines = sf.dose_table({("perpr-haiku", 0): a, ("perpr-haiku", 1): b, ("perpr-haiku", 2): t})
        self.assertIn("perpr-haiku", lines[1])
        self.assertIn("1.50", lines[1])  # reds mean over the two observable trials
        self.assertIn("7.50", lines[1])  # dispatches mean
        self.assertTrue(lines[1].rstrip().endswith("1"))  # one truncated


def _hook_record(event: str, outcome: str, **extra) -> dict:
    """One convoy 0.12.0 hook.log record (``interface/hook.py::_record`` + verdict fields)."""
    rec = {
        "ts": "2026-09-04T10:00:00.000+00:00",
        "event": event,
        "leg": "judge" if event == "SubagentStop" else "messenger",
        "tool_name": "" if event == "SubagentStop" else "Task",
        "tool_use_id": "",
        "session_id": "sess",
        "agent_id": "agent-1",
        "agent_type": "general-purpose",
        "model": "claude-haiku-4-5-20251001",
        "stop_hook_active": False,
        "cwd": "C:/stage",
        "convoy_version": "0.12.0",
        "outcome": outcome,
        "exit_code": 2 if outcome == "blocked" else 0,
    }
    if outcome in ("blocked", "completed"):
        rec.update(
            series_id="multiagent-composition-gate",
            phases=["bools"],
            blocking_red=outcome == "blocked",
            independent_red=False,
            counts={"selected": 3, "passed": 2, "failed": 1},
            checks=[],
            repair_brief="" if outcome == "completed" else "## Failing checks\n",
            gate_ms=1200,
        )
    rec.update(extra)
    return rec


def _write_hook_log(d: Path, name: str, records: list[dict]) -> Path:
    p = d / name
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return p


class HookLogTests(unittest.TestCase):
    def test_name_parsing_accepts_the_tag_and_the_stem_forms(self):
        self.assertEqual(
            sf.parse_hook_log_name(f"{BANK}--hook2-haiku--exprlang--r3--hook.log"),
            ("hook2-haiku", 3),
        )
        self.assertEqual(
            sf.parse_hook_log_name(f"{BANK}--hook2-sonnet--exprlang--r12--a1--{AFTER}--hook.log"),
            ("hook2-sonnet", 12),
        )
        self.assertIsNone(sf.parse_hook_log_name("untagged--hook.log"))
        self.assertIsNone(sf.parse_hook_log_name(f"{BANK}--hook2-haiku--exprlang--r3.ndjson"))

    def test_firings_count_red_judge_records_only(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            log = _write_hook_log(
                d,
                f"{BANK}--hook2-haiku--exprlang--r0--hook.log",
                [
                    _hook_record("SubagentStop", "blocked", blocked_stop=True),
                    _hook_record("SubagentStop", "completed", stop_hook_active=True),
                    _hook_record("PostToolUse", "completed"),
                    _hook_record("SubagentStop", "skipped", reason="read-only subagent"),
                    _hook_record("SubagentStop", "blocked", blocked_stop=False),
                    _hook_record("PostToolUse", "blocked"),  # the messenger reuses the verdict
                    _hook_record("SubagentStop", "usage", error="unknown phase"),
                ],
            )
            self.assertEqual(sf.read_hook_log(log), (5, 2))
            orch = _write(d, "o.ndjson", [_init("C:/stage")])
            f = sf.trial_facts("hook2-haiku", 0, [orch], "bank-v2", hook_log=log)
            self.assertTrue(f.hook_log_present)
            self.assertEqual((f.hook_log_stops, f.hook_log_firings), (5, 2))
            self.assertEqual(f.hook_log_file, log.name)
            g = sf.trial_facts("hook2-haiku", 0, [orch], "bank-v2")
            self.assertFalse(g.hook_log_present)
            self.assertEqual((g.hook_log_stops, g.hook_log_firings), (0, 0))

    def test_hook_logs_keyed_and_void_aware(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            stale = _write_hook_log(
                d,
                f"{BANK}--hook2-haiku--exprlang--r3--hook.log",
                [_hook_record("SubagentStop", "blocked")],
            )
            live = _write_hook_log(
                d,
                f"{BANK}--hook2-sonnet--exprlang--r3--hook.log",
                [_hook_record("SubagentStop", "completed")],
            )
            _write_hook_log(d, "junk--hook.log", [])
            got = sf.hook_logs([d])
            self.assertEqual(got, {("hook2-haiku", 3): stale, ("hook2-sonnet", 3): live})
            # a void stamped after the file's mtime hides the stale file
            far_future = int(stale.stat().st_mtime * 1000) + 10_000_000
            got = sf.hook_logs([d], {("hook2-haiku", 3): far_future})
            self.assertEqual(got, {("hook2-sonnet", 3): live})

    def test_all_facts_attaches_the_hook_log_and_the_dose_table_shows_it(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            rows = [
                {
                    "bank": BANK,
                    "kind": "trial",
                    "scenario": "hook2-haiku",
                    "config_hash": "h9",
                    "repeat": 0,
                    "status": "completed",
                    "verifier_results": {},
                }
            ]
            ledger = d / "ledger.jsonl"
            ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            _write(
                d,
                f"{BANK}--hook2-haiku--exprlang--r0--a1--{AFTER}.ndjson",
                [_init("C:/stage"), _use("Agent", {"prompt": "x"}, "a1"), _result("a1", "ok")],
            )
            _write_hook_log(
                d,
                f"{BANK}--hook2-haiku--exprlang--r0--hook.log",
                [
                    _hook_record("SubagentStop", "blocked", blocked_stop=True),
                    _hook_record("SubagentStop", "completed", stop_hook_active=True),
                ],
            )
            facts = sf.all_facts(ledger, [d], "bank-v2")
            f = facts[("hook2-haiku", 0)]
            self.assertTrue(f.hook_log_present)
            self.assertEqual((f.hook_log_stops, f.hook_log_firings), (2, 1))
            lines = sf.dose_table(facts)
            self.assertIn("hook", lines[0])
            self.assertIn("{1:1}", lines[1])  # the hook column
            self.assertIn("1.00", lines[1])  # hook reds count as gate reds per trial

    def test_placebo2_command_is_a_placebo_call(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            evs = [
                _init("C:/stage"),
                _use("Bash", {"command": "python C:/h/placebo_gate2.py ."}, "p1"),
                _result("p1", f"{sf.PLACEBO_RED}: re-run", is_error=True),
                _use("Bash", {"command": "python C:/h/placebo_gate2.py ."}, "p2"),
                _result("p2", "ok"),
            ]
            orch = _write(d, "o.ndjson", evs)
            f = sf.trial_facts("placebo2-haiku", 1, [orch], "bank-v2")
            self.assertEqual((f.placebo_calls, f.placebo_reds), (2, 1))
            self.assertEqual(f.exposure, [])


class ArmingVerdictTests(unittest.TestCase):
    @staticmethod
    def _facts(**per_scenario) -> dict:
        return {
            (scenario, 0): sf.TrialFacts(scenario, 0, [], "o", **fields)
            for scenario, fields in per_scenario.items()
        }

    def test_armed_iteration2_cells_pass(self):
        facts = self._facts(
            **{
                "control2-haiku": {},
                "placebo2-haiku": {"placebo_calls": 6, "placebo_reds": 1},
                "perpr2-haiku": {"driver_calls": 6, "driver_reds": 1},
                "hook2-haiku": {
                    "hook_log_present": True,
                    "hook_log_stops": 6,
                    "hook_log_firings": 1,
                },
            }
        )
        verdicts = sf.arming_verdicts(facts)
        self.assertEqual([v[2] for v in verdicts], ["PASS"] * 4)
        self.assertEqual({v[0] for v in verdicts}, {k[0] for k in facts})

    def test_each_unarmed_case_fails_with_its_reason(self):
        facts = self._facts(
            **{
                "control2-haiku": {"driver_calls": 1},
                "control2-sonnet": {"hook_log_present": True},
                "placebo2-haiku": {"placebo_calls": 6, "placebo_reds": 0},
                "placebo2-sonnet": {"placebo_reds": 1, "driver_calls": 2},
                "perpr2-haiku": {"driver_calls": 4},
                "perpr2-sonnet": {"driver_calls": 6, "placebo_calls": 1},
                "hook2-haiku": {"hook_log_present": False},
                "hook2-sonnet": {"hook_log_present": True, "driver_calls": 1},
            }
        )
        verdicts = {v[0]: (v[2], v[3]) for v in sf.arming_verdicts(facts)}
        self.assertTrue(all(v[0] == "FAIL" for v in verdicts.values()), verdicts)
        self.assertIn("driver_calls != 0", verdicts["control2-haiku"][1])
        self.assertIn("hook_log present", verdicts["control2-sonnet"][1])
        self.assertIn("placebo_reds < 1", verdicts["placebo2-haiku"][1])
        self.assertIn("driver_calls != 0", verdicts["placebo2-sonnet"][1])
        self.assertIn("driver_calls < 5", verdicts["perpr2-haiku"][1])
        self.assertIn("placebo_calls != 0", verdicts["perpr2-sonnet"][1])
        self.assertIn("hook_log absent", verdicts["hook2-haiku"][1])
        self.assertIn("driver_calls != 0 (orchestrator)", verdicts["hook2-sonnet"][1])

    def test_unknown_arms_skip_and_repeat_filters(self):
        facts = {
            ("perpr-haiku", 0): sf.TrialFacts("perpr-haiku", 0, [], "o", driver_calls=6),
            ("perpr2-haiku", 0): sf.TrialFacts("perpr2-haiku", 0, [], "o", driver_calls=6),
            ("perpr2-haiku", 1): sf.TrialFacts("perpr2-haiku", 1, [], "o", driver_calls=0),
        }
        verdicts = sf.arming_verdicts(facts)
        self.assertEqual(
            [(v[0], v[1], v[2]) for v in verdicts],
            [
                ("perpr-haiku", 0, "SKIP"),
                ("perpr2-haiku", 0, "PASS"),
                ("perpr2-haiku", 1, "FAIL"),
            ],
        )
        only_r0 = sf.arming_verdicts(facts, repeat=0)
        self.assertEqual([(v[0], v[1]) for v in only_r0], [("perpr-haiku", 0), ("perpr2-haiku", 0)])

    def test_cli_arming_check_exits_two_on_a_fail(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            rows = [
                {
                    "bank": BANK,
                    "kind": "trial",
                    "scenario": "hook2-haiku",
                    "config_hash": "h9",
                    "repeat": 0,
                    "status": "completed",
                    "verifier_results": {},
                }
            ]
            ledger = d / "ledger.jsonl"
            ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            _write(d, f"{BANK}--hook2-haiku--exprlang--r0--a1--{AFTER}.ndjson", [_init("C:/stage")])
            argv = ["--ledger", str(ledger), "--streams", str(d), "--task-dir-name", "bank-v2"]
            self.assertEqual(sf.main(argv + ["--arming-check"]), 2)  # no hook.log: hook2 unarmed
            _write_hook_log(
                d,
                f"{BANK}--hook2-haiku--exprlang--r0--hook.log",
                [_hook_record("SubagentStop", "completed")],
            )
            self.assertEqual(sf.main(argv + ["--arming-check"]), 0)
            self.assertEqual(
                sf.main(argv + ["--arming-check", "--repeat", "7"]), 2
            )  # nothing matched


if __name__ == "__main__":
    unittest.main()
