"""Per-trial facts from the persisted streams of a multiagent bank, read as EVENTS.

The readout's first attestation counted substrings over every stream file sharing a tag,
which (a) counted a driver path in brief echoes and tool results as if it were an
execution, (b) folded a voided trial's stream into its re-bought successor's, and (c)
folded the final arm's fix spawns into the orchestrator. The 2026-09-03 blind review
caught all three. This module reads each stream as JSON events, keeps only the streams
that belong to the trial the ledger counts (the cluster after the key's void, if any),
tells the orchestrator from its spawns, and counts tool_use events:

- ``agent_dispatches``: orchestrator-level ``Agent``/``Task`` tool_use events.
- ``driver_calls`` / ``driver_reds``: orchestrator-level Bash/PowerShell calls that run the
  convoy gate driver and returned a result; red = the result carries a blocked outcome
  (a red gate exits 1 and is flagged ``is_error`` while having genuinely run).
- ``placebo_calls`` / ``placebo_reds``: the same for the placebo gate.
- ``spawn_driver_calls``: driver calls that ran below the orchestrator — inside a subagent
  or inside a fix spawn (the final arm's loop) — and are therefore not the orchestrator's dose.
- A result the host refused ("requires approval" in headless mode) is not an execution.
- ``exposure``: every Read/Glob/Grep/Write/Edit/NotebookEdit/Bash whose input names a path
  under the bank's task directory other than ``prompts/`` — the oracle, the reference
  solution, the fixture tree, or the harness internals — at any level (subagent tool calls
  carry ``parent_tool_use_id``). Brief-mandated Bash executions of the driver or the placebo
  gate are not exposure; a Read of the driver is.
- ``models``: the dated model snapshots seen in assistant events.
- ``hook_log_present`` / ``hook_log_stops`` / ``hook_log_firings``: the hook arms' gate runs
  inside convoy's ``SubagentStop`` hook, not as a tool call, so it leaves no tool_use event.
  Their Stop hook copies the workspace's ``.convoy/hook.log`` into the stream dir as
  ``<bank>--<scenario>--<task>--r<repeat>--hook.log`` (one JSON record per firing; convoy
  0.12.0 ``interface/hook.py``). ``stops`` counts the judge leg's records (``event ==
  "SubagentStop"``), ``firings`` those whose ``outcome`` is ``blocked`` — a red gate, whether
  it held the subagent (``blocked_stop: true``) or recorded a residual red on the retry.
- ``arming_verdicts``: per-arm arming criteria for the iteration-2 arms, evaluated on the
  facts above (``--arming-check``; exit 2 on any FAIL).

CLI (from the fathom repo):
    uv run python tools/stream_facts.py --ledger ledger/<bank>.jsonl \
        --streams streams-multiagent/<pilot> --streams streams-multiagent/<main> \
        [--task-dir-name multiagent-composition-v2] [--exposure] [--dose] [--fail-on-exposure]
        [--per-trial] [--arming-check [--repeat N]]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from fathom.ledger import apply_voids  # noqa: E402

DRIVER_MARKER = "run_convoy_gate.py"
PLACEBO_MARKER = "placebo_gate.py"
PLACEBO2_MARKER = "placebo_gate2.py"  # iteration 2's equal-content placebo
PLACEBO_MARKERS = (PLACEBO_MARKER, PLACEBO2_MARKER)
PLACEBO_RED = "transient check failed"  # shared by placebo_gate.py and placebo_gate2.py
# A hook.log record whose gate was red: convoy's judge writes outcome "blocked" (blocking_red).
HOOK_RED_OUTCOMES = {"blocked"}
HOOK_JUDGE_EVENT = "SubagentStop"
EXPOSURE_TOOLS = {"Read", "Glob", "Grep", "Write", "Edit", "NotebookEdit", "Bash", "PowerShell"}
DISPATCH_TOOLS = {"Agent", "Task"}
_TAG = re.compile(
    r"^(?P<bank>.+?)--(?P<scenario>[^-]+-[^-]+)--(?P<task>[^-]+)--r(?P<repeat>\d+)--a\d+--(?P<epoch>\d+)\.ndjson$"
)
# The Stop hook writes ``<FATHOM_STREAM_TAG>--hook.log`` (tag = bank--scenario--task--rN);
# a stem carrying the adapter's ``--aN--<epoch>`` suffix is accepted too.
_HOOK_LOG = re.compile(
    r"^(?P<bank>.+?)--(?P<scenario>[^-]+-[^-]+)--(?P<task>[^-]+)--r(?P<repeat>\d+)(?:--.*)?--hook\.log$"
)
_DATED = re.compile(r"claude-[a-z0-9-]+-20\d{6}")


@dataclass
class Exposure:
    file: str
    tool: str
    path: str
    level: str  # "orchestrator" | "subagent"


@dataclass
class TrialFacts:
    scenario: str
    repeat: int
    files: list[str]
    orchestrator: str
    agent_dispatches: int = 0
    driver_calls: int = 0
    driver_reds: int = 0
    placebo_calls: int = 0
    placebo_reds: int = 0
    spawn_driver_calls: int = 0
    exposure: list[Exposure] = field(default_factory=list)
    models: set[str] = field(default_factory=set)
    truncated: bool = False  # no result event in the orchestrator stream
    hook_log_present: bool = False  # the arm's Stop hook copied a .convoy/hook.log
    hook_log_stops: int = 0  # judge-leg records (SubagentStop firings)
    hook_log_firings: int = 0  # judge-leg records whose gate was red (outcome blocked)
    hook_log_file: str = ""


def parse_tag(name: str) -> tuple[str, int, int] | None:
    """(scenario, repeat, end_epoch_ms) from a stream file name, or None for untagged."""
    m = _TAG.match(name)
    if not m:
        return None
    return m.group("scenario"), int(m.group("repeat")), int(m.group("epoch"))


def parse_hook_log_name(name: str) -> tuple[str, int] | None:
    """(scenario, repeat) from a copied hook.log file name, or None."""
    m = _HOOK_LOG.match(name)
    if not m:
        return None
    return m.group("scenario"), int(m.group("repeat"))


def hook_logs(
    stream_dirs: list[Path], void_at: dict[tuple[str, int], int] | None = None
) -> dict[tuple[str, int], Path]:
    """The copied hook.log per (scenario, repeat); the newest file wins across dirs.

    A file older than the key's void (mtime before ``voided_at``) belongs to the voided
    trial and is ignored — the Stop hook overwrites the same name on a re-buy, so a stale
    file survives only when the re-bought trial's hook never wrote a log.
    """
    out: dict[tuple[str, int], tuple[float, Path]] = {}
    for d in stream_dirs:
        for f in sorted(d.glob("*--hook.log")):
            key = parse_hook_log_name(f.name)
            if key is None:
                continue
            mtime = f.stat().st_mtime
            cut = (void_at or {}).get(key)
            if cut is not None and mtime * 1000 <= cut:
                continue
            if key not in out or mtime > out[key][0]:
                out[key] = (mtime, f)
    return {k: f for k, (_, f) in out.items()}


def read_hook_log(path: Path) -> tuple[int, int]:
    """(judge-leg records, judge-leg records whose gate was red) from one hook.log."""
    stops = reds = 0
    for rec in events(path):
        if not isinstance(rec, dict) or rec.get("event") != HOOK_JUDGE_EVENT:
            continue
        stops += 1
        if rec.get("outcome") in HOOK_RED_OUTCOMES:
            reds += 1
    return stops, reds


def events(path: Path):
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _content(e: dict) -> list[dict]:
    m = e.get("message")
    if not isinstance(m, dict):
        return []
    c = m.get("content")
    if not isinstance(c, list):
        return []
    return [x for x in c if isinstance(x, dict)]


def _result_text(c: dict) -> str:
    cc = c.get("content")
    if isinstance(cc, str):
        return cc
    if isinstance(cc, list):
        return " ".join(str(x.get("text", "")) for x in cc if isinstance(x, dict))
    return ""


def _executed(result_text: str) -> bool:
    """False when the host refused the command (a permission prompt in headless mode)."""
    return "requires approval" not in result_text and not result_text.startswith(
        "This Bash command contains multiple operations"
    )


def init_cwd(path: Path) -> str | None:
    for e in events(path):
        if e.get("type") == "system" and e.get("subtype") == "init":
            return e.get("cwd")
        # init is the first line; stop early on anything else
        break
    return None


def ledger_keys(ledger: Path) -> tuple[set[tuple[str, int]], dict[tuple[str, int], int]]:
    """Counted (scenario, repeat) keys after voids, and per key the void time (epoch ms)."""
    rows = [
        json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    kept = {
        (r["scenario"], int(r["repeat"]))
        for r in apply_voids(rows)
        if r.get("kind") == "trial" and r.get("status") == "completed"
    }
    void_at: dict[tuple[str, int], int] = {}
    for r in rows:
        if r.get("kind") != "void":
            continue
        ts = r.get("voided_at") or ""
        epoch = _iso_to_epoch_ms(ts)
        key = (str(r.get("scenario")), int(r.get("repeat", -1)))
        if epoch is not None:
            void_at[key] = max(void_at.get(key, 0), epoch)
    return kept, void_at


def _iso_to_epoch_ms(ts: str) -> int | None:
    from datetime import datetime, timezone

    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def surviving_streams(ledger: Path, stream_dirs: list[Path]) -> dict[tuple[str, int], list[Path]]:
    """The stream files of the trial the ledger counts, per (scenario, repeat).

    Files sharing a tag are clustered by their init ``cwd`` (the per-trial stage dir). The
    surviving cluster is the one whose files all postdate the key's void (when the key was
    voided) — the re-bought trial — else the cluster with the latest end time.
    """
    kept, void_at = ledger_keys(ledger)
    by_key: dict[tuple[str, int], list[tuple[int, Path]]] = defaultdict(list)
    for d in stream_dirs:
        for f in sorted(d.glob("*.ndjson")):
            tag = parse_tag(f.name)
            if tag is None:
                continue
            scenario, repeat, epoch = tag
            if (scenario, repeat) in kept:
                by_key[(scenario, repeat)].append((epoch, f))
    out: dict[tuple[str, int], list[Path]] = {}
    for key, files in by_key.items():
        clusters: dict[str, list[tuple[int, Path]]] = defaultdict(list)
        for epoch, f in files:
            clusters[init_cwd(f) or f.name].append((epoch, f))
        cut = void_at.get(key)
        candidates = [
            c for c in clusters.values() if cut is None or all(epoch > cut for epoch, _ in c)
        ]
        if not candidates:
            candidates = list(clusters.values())
        chosen = max(candidates, key=lambda c: max(epoch for epoch, _ in c))
        out[key] = [f for _, f in sorted(chosen)]
    return out


def _mentions_task_dir(text: str, task_dir_name: str) -> str | None:
    """The first path-like token naming the bank task dir outside prompts/, else None."""
    for m in re.finditer(r"[A-Za-z]:[\\/][^\s\"']+|/[^\s\"']+", text):
        tok = m.group(0).replace("\\\\", "/").replace("\\", "/")
        if f"tasks/{task_dir_name}" in tok and "/prompts" not in tok:
            return tok
    return None


def trial_facts(
    scenario: str,
    repeat: int,
    files: list[Path],
    task_dir_name: str,
    hook_log: Path | None = None,
) -> TrialFacts:
    orchestrator = files[0]  # earliest end time in the cluster is the orchestrator
    facts = TrialFacts(scenario, repeat, [f.name for f in files], orchestrator.name)
    if hook_log is not None:
        facts.hook_log_present = True
        facts.hook_log_file = hook_log.name
        facts.hook_log_stops, facts.hook_log_firings = read_hook_log(hook_log)
    for f in files:
        is_orch = f is orchestrator
        pending: dict[str, tuple[str, bool]] = {}  # tool_use id -> (kind, orchestrator-level)
        saw_result = False
        for e in events(f):
            if e.get("type") == "result":
                saw_result = True
            level_orch = e.get("parent_tool_use_id") in (None, "")
            if e.get("type") == "assistant":
                for m in _DATED.findall(json.dumps(e.get("message", {}).get("model", ""))):
                    facts.models.add(m.split("claude-", 1)[1])
            for c in _content(e):
                if c.get("type") == "tool_use":
                    name = str(c.get("name"))
                    raw = json.dumps(c.get("input") or {})
                    if name in DISPATCH_TOOLS and level_orch and is_orch:
                        facts.agent_dispatches += 1
                    if name in ("Bash", "PowerShell"):
                        if DRIVER_MARKER in raw:
                            pending[str(c.get("id"))] = ("driver", level_orch and is_orch)
                        elif any(m in raw for m in PLACEBO_MARKERS):
                            pending[str(c.get("id"))] = ("placebo", level_orch and is_orch)
                    if name in EXPOSURE_TOOLS:
                        mandated = name in ("Bash", "PowerShell") and (
                            DRIVER_MARKER in raw or any(m in raw for m in PLACEBO_MARKERS)
                        )
                        hit = None if mandated else _mentions_task_dir(raw, task_dir_name)
                        if hit:
                            facts.exposure.append(
                                Exposure(
                                    f.name, name, hit, "orchestrator" if level_orch else "subagent"
                                )
                            )
                elif c.get("type") == "tool_result" and str(c.get("tool_use_id")) in pending:
                    kind, orch_level = pending.pop(str(c.get("tool_use_id")))
                    text = _result_text(c)
                    if not _executed(text):
                        continue  # the host refused the command; nothing ran
                    if kind == "driver":
                        # a red gate exits 1 and is flagged is_error while having run: the
                        # verdict is read from the envelope, never from the error flag
                        red = '"outcome": "blocked"' in text or "[RED]" in text
                        if orch_level:
                            facts.driver_calls += 1
                            facts.driver_reds += int(red)
                        else:
                            facts.spawn_driver_calls += 1
                    else:
                        if orch_level:
                            facts.placebo_calls += 1
                            facts.placebo_reds += int(PLACEBO_RED in text)
        if is_orch and not saw_result:
            facts.truncated = True
    return facts


def all_facts(
    ledger: Path, stream_dirs: list[Path], task_dir_name: str
) -> dict[tuple[str, int], TrialFacts]:
    _, void_at = ledger_keys(ledger)
    logs = hook_logs(stream_dirs, void_at)
    return {
        key: trial_facts(key[0], key[1], files, task_dir_name, logs.get(key))
        for key, files in sorted(surviving_streams(ledger, stream_dirs).items())
    }


def dose_table(facts: dict[tuple[str, int], TrialFacts]) -> list[str]:
    """Per cell: n, gate reds per trial (mean + distribution), Agent dispatches per trial."""
    cells: dict[str, list[TrialFacts]] = defaultdict(list)
    for (scenario, _), f in facts.items():
        cells[scenario].append(f)
    lines = [
        f"{'cell':16} {'n':>3}  {'reds/trial':>10}  {'distribution':22} {'dispatches/trial':>16}  distribution   driver calls (orch)  hook            truncated"
    ]
    for scenario in sorted(cells):
        fs = [f for f in cells[scenario] if not f.truncated]
        n = len(fs)
        # a red is a red whichever actor ran the gate: the driver, the placebo, or the hook
        reds = [f.driver_reds + f.placebo_reds + f.hook_log_firings for f in fs]
        disp = [f.agent_dispatches for f in fs]
        drv = [f.driver_calls for f in fs]
        hook = [f.hook_log_firings for f in fs if f.hook_log_present]
        trunc = sum(1 for f in cells[scenario] if f.truncated)

        def dist(xs: list[int]) -> str:
            return "{" + ", ".join(f"{k}:{v}" for k, v in sorted(Counter(xs).items())) + "}"

        lines.append(
            f"{scenario:16} {n:>3}  {statistics.mean(reds) if reds else 0:>10.2f}  {dist(reds):22} "
            f"{statistics.mean(disp) if disp else 0:>16.2f}  {dist(disp):14} {dist(drv):20} "
            f"{(dist(hook) if hook else '-'):15} {trunc}"
        )
    return lines


# Iteration-2 arming criteria, per arm (the scenario name's prefix before its tier).
# control2 must show no gate of any kind; placebo2 must have run the placebo to a red and
# never the driver; perpr2 must have driven the gate at least once per PR (five PRs) and
# never the placebo; hook2's gate lives in the hook, so the copied hook.log is the
# attestation and the driver must not have been run by the orchestrator.
ITER2_ARMS = ("control2", "placebo2", "perpr2", "hook2")


def arming_verdicts(
    facts: dict[tuple[str, int], TrialFacts], repeat: int | None = None
) -> list[tuple[str, int, str, str]]:
    """(scenario, repeat, PASS|FAIL|SKIP, reason) per trial; SKIP for arms without criteria."""
    out: list[tuple[str, int, str, str]] = []
    for (scenario, rep), f in sorted(facts.items()):
        if repeat is not None and rep != repeat:
            continue
        arm = scenario.rsplit("-", 1)[0]
        seen = (
            f"driver={f.driver_calls} placebo={f.placebo_calls}/{f.placebo_reds} "
            f"hook_log={'present' if f.hook_log_present else 'absent'}"
            f"({f.hook_log_stops} stops, {f.hook_log_firings} red)"
            f"{' TRUNCATED' if f.truncated else ''}"
        )
        failures: list[str] = []
        if arm == "control2":
            if f.driver_calls != 0:
                failures.append("driver_calls != 0")
            if f.placebo_calls != 0:
                failures.append("placebo_calls != 0")
            if f.hook_log_firings != 0:
                failures.append("hook_log_firings != 0")
            if f.hook_log_present:
                failures.append("hook_log present")
        elif arm == "placebo2":
            if f.placebo_reds < 1:
                failures.append("placebo_reds < 1")
            if f.driver_calls != 0:
                failures.append("driver_calls != 0")
        elif arm == "perpr2":
            if f.driver_calls < 5:
                failures.append("driver_calls < 5")
            if f.placebo_calls != 0:
                failures.append("placebo_calls != 0")
        elif arm == "hook2":
            if not f.hook_log_present:
                failures.append("hook_log absent")
            if f.driver_calls != 0:
                failures.append("driver_calls != 0 (orchestrator)")
        else:
            out.append((scenario, rep, "SKIP", f"no arming criteria for arm {arm!r}; {seen}"))
            continue
        if failures:
            out.append((scenario, rep, "FAIL", "; ".join(failures) + f"; {seen}"))
        else:
            out.append((scenario, rep, "PASS", seen))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--streams", action="append", required=True, help="repeatable")
    ap.add_argument("--task-dir-name", default="multiagent-composition-v2")
    ap.add_argument("--dose", action="store_true", help="print the per-cell dose table")
    ap.add_argument("--exposure", action="store_true", help="list trials that touched the task dir")
    ap.add_argument("--per-trial", action="store_true", help="print one line per counted trial")
    ap.add_argument(
        "--fail-on-exposure", action="store_true", help="exit 1 if any counted trial is exposed"
    )
    ap.add_argument(
        "--arming-check",
        action="store_true",
        help="evaluate the iteration-2 per-arm arming criteria; exit 2 on any FAIL",
    )
    ap.add_argument(
        "--repeat", type=int, default=None, help="restrict --arming-check to this repeat index"
    )
    args = ap.parse_args(argv)

    facts = all_facts(Path(args.ledger), [Path(s) for s in args.streams], args.task_dir_name)
    print(f"counted trials with a surviving stream: {len(facts)}")
    if args.per_trial:
        for (scenario, repeat), f in facts.items():
            print(
                f"  {scenario:16} r{repeat:<3} files={len(f.files)} dispatches={f.agent_dispatches:>2} "
                f"driver={f.driver_calls:>2} reds={f.driver_reds} placebo={f.placebo_calls}/{f.placebo_reds} "
                f"spawn_driver={f.spawn_driver_calls} exposed={len(f.exposure)} "
                f"hook={(f'{f.hook_log_firings}/{f.hook_log_stops}' if f.hook_log_present else '-')} "
                f"models={','.join(sorted(f.models)) or 'undated-alias-only'}{' TRUNCATED' if f.truncated else ''}"
            )
    if args.dose:
        print()
        print(
            "DOSE (pre-registration addendum 5): gate reds and fix dispatches per trial, per cell"
        )
        print("\n".join(dose_table(facts)))
    exposed = {k: f for k, f in facts.items() if f.exposure}
    if args.exposure:
        print()
        print(
            f"EXPOSURE: counted trials whose transcript names the task dir outside prompts/: {len(exposed)}"
        )
        for (scenario, repeat), f in exposed.items():
            paths = Counter(
                (x.tool, x.level, x.path.rsplit(f"tasks/{args.task_dir_name}", 1)[-1][:60])
                for x in f.exposure
            )
            print(f"  {scenario} r{repeat}:")
            for (tool, level, path), n in sorted(paths.items()):
                print(f"    {tool:6} {level:12} x{n:<3} ...{path}")
    if args.fail_on_exposure and exposed:
        print(f"FAIL: {len(exposed)} counted trial(s) exposed to the task dir", file=sys.stderr)
        return 1
    if args.arming_check:
        print()
        print("ARMING CHECK (iteration-2 criteria; hook = red/stops from the copied hook.log)")
        verdicts = arming_verdicts(facts, args.repeat)
        for scenario, repeat, verdict, reason in verdicts:
            print(f"  {verdict:4} {scenario:16} r{repeat:<3} {reason}")
        failed = sum(1 for v in verdicts if v[2] == "FAIL")
        if not verdicts:
            print("FAIL: no counted trial matched the arming check", file=sys.stderr)
            return 2
        if failed:
            print(f"FAIL: {failed} trial(s) failed the arming check", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
