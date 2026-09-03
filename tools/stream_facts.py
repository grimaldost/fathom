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

CLI (from the fathom repo):
    uv run python tools/stream_facts.py --ledger ledger/<bank>.jsonl \
        --streams streams-multiagent/<pilot> --streams streams-multiagent/<main> \
        [--task-dir-name multiagent-composition-v2] [--exposure] [--dose] [--fail-on-exposure]
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
PLACEBO_RED = "transient check failed"
EXPOSURE_TOOLS = {"Read", "Glob", "Grep", "Write", "Edit", "NotebookEdit", "Bash", "PowerShell"}
DISPATCH_TOOLS = {"Agent", "Task"}
_TAG = re.compile(
    r"^(?P<bank>.+?)--(?P<scenario>[^-]+-[^-]+)--(?P<task>[^-]+)--r(?P<repeat>\d+)--a\d+--(?P<epoch>\d+)\.ndjson$"
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


def parse_tag(name: str) -> tuple[str, int, int] | None:
    """(scenario, repeat, end_epoch_ms) from a stream file name, or None for untagged."""
    m = _TAG.match(name)
    if not m:
        return None
    return m.group("scenario"), int(m.group("repeat")), int(m.group("epoch"))


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


def trial_facts(scenario: str, repeat: int, files: list[Path], task_dir_name: str) -> TrialFacts:
    orchestrator = files[0]  # earliest end time in the cluster is the orchestrator
    facts = TrialFacts(scenario, repeat, [f.name for f in files], orchestrator.name)
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
                        elif PLACEBO_MARKER in raw:
                            pending[str(c.get("id"))] = ("placebo", level_orch and is_orch)
                    if name in EXPOSURE_TOOLS:
                        mandated = name in ("Bash", "PowerShell") and (
                            DRIVER_MARKER in raw or PLACEBO_MARKER in raw
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
    return {
        key: trial_facts(key[0], key[1], files, task_dir_name)
        for key, files in sorted(surviving_streams(ledger, stream_dirs).items())
    }


def dose_table(facts: dict[tuple[str, int], TrialFacts]) -> list[str]:
    """Per cell: n, gate reds per trial (mean + distribution), Agent dispatches per trial."""
    cells: dict[str, list[TrialFacts]] = defaultdict(list)
    for (scenario, _), f in facts.items():
        cells[scenario].append(f)
    lines = [
        f"{'cell':16} {'n':>3}  {'reds/trial':>10}  {'distribution':22} {'dispatches/trial':>16}  distribution   driver calls (orch)  truncated"
    ]
    for scenario in sorted(cells):
        fs = [f for f in cells[scenario] if not f.truncated]
        n = len(fs)
        reds = [f.driver_reds + f.placebo_reds for f in fs]
        disp = [f.agent_dispatches for f in fs]
        drv = [f.driver_calls for f in fs]
        trunc = sum(1 for f in cells[scenario] if f.truncated)

        def dist(xs: list[int]) -> str:
            return "{" + ", ".join(f"{k}:{v}" for k, v in sorted(Counter(xs).items())) + "}"

        lines.append(
            f"{scenario:16} {n:>3}  {statistics.mean(reds) if reds else 0:>10.2f}  {dist(reds):22} "
            f"{statistics.mean(disp) if disp else 0:>16.2f}  {dist(disp):14} {dist(drv):20} {trunc}"
        )
    return lines


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
    args = ap.parse_args(argv)

    facts = all_facts(Path(args.ledger), [Path(s) for s in args.streams], args.task_dir_name)
    print(f"counted trials with a surviving stream: {len(facts)}")
    if args.per_trial:
        for (scenario, repeat), f in facts.items():
            print(
                f"  {scenario:16} r{repeat:<3} files={len(f.files)} dispatches={f.agent_dispatches:>2} "
                f"driver={f.driver_calls:>2} reds={f.driver_reds} placebo={f.placebo_calls}/{f.placebo_reds} "
                f"spawn_driver={f.spawn_driver_calls} exposed={len(f.exposure)} "
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
