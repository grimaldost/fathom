"""Tests for tools/stream_facts.py — event-level per-trial facts from persisted streams.

Synthetic streams shaped like the live CLI's stream-json (init line, assistant tool_use,
user tool_result, result), a voided predecessor cluster, a fix-spawn cluster, an exposure
read inside a subagent, and a driver call that came back red.
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


if __name__ == "__main__":
    unittest.main()
