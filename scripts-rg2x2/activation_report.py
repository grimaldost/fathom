#!/usr/bin/env python3
"""RG-2x2 activation report: parse persisted trial streams + ledger into the
pre-registered outcome tables (activation / gate compliance / footprint).

Usage:
    python activation_report.py <streams_dir> <ledger_dir>

Stream filenames: {bank}--{scenario}--{task}--r{repeat}--a{attempt}--{ts}.ndjson
Scenario names:   rg2x2-{bankshort}-{arm}-{tier}

Stdlib only. Reads only; writes nothing.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

TARGETS = {
    "e1-debug": ["systematic-debugging"],
    "e1-data": ["data-engineering-discipline"],
    "e1-verif": ["verification-before-completion"],
}
ADJACENT = {
    "e1-verif": ["test-driven-development"],
}
PROXY = {
    "e1-debug": "second_site_fixed",
    "e1-data": "output_correct_on_subtle_case",
    "e1-verif": "regression_check_present",
}
ARMS = ["ctrl", "reg", "gate", "both"]
TIERS = ["haiku", "sonnet"]


def parse_stream(path: Path) -> dict:
    skill_inputs: list[str] = []
    text_parts: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") != "assistant":
            continue
        for blk in (ev.get("message") or {}).get("content") or []:
            if not isinstance(blk, dict):
                continue
            if blk.get("type") == "tool_use" and blk.get("name") == "Skill":
                skill_inputs.append(json.dumps(blk.get("input") or {}))
            elif blk.get("type") == "text":
                text_parts.append(blk.get("text") or "")
    return {
        "skill_inputs": skill_inputs,
        "gate_line": bool(re.search(r"skill check:", " ".join(text_parts), re.I)),
    }


def main() -> int:
    streams_dir, ledger_dir = Path(sys.argv[1]), Path(sys.argv[2])

    # Last attempt per trial wins (matches the recorded RunRecord).
    latest: dict[tuple, Path] = {}
    for f in streams_dir.glob("*.ndjson"):
        m = re.match(r"(.+?)--(.+?)--(.+?)--r(\d+)--a(\d+)--(\d+)\.ndjson$", f.name)
        if not m:
            continue
        bank, scenario, task, repeat, attempt, ts = m.groups()
        key = (bank, scenario, task, int(repeat))
        prev = latest.get(key)
        if prev is None or (int(attempt), int(ts)) > prev[0]:
            latest[key] = ((int(attempt), int(ts)), f)  # type: ignore[assignment]

    # Footprint from ledger trial records.
    footprint: dict[tuple, bool] = {}
    for lf in ledger_dir.glob("*.jsonl"):
        for line in lf.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") != "trial" or r.get("status") != "completed":
                continue
            vr = r.get("verifier_results") or {}
            pk = PROXY.get(r.get("bank", ""))
            footprint[(r["bank"], r["scenario"], r["task_id"], r.get("repeat", 0))] = bool(
                vr.get(pk)
            )

    rows = []
    for (bank, scenario, task, repeat), (_, f) in sorted(latest.items()):
        m = re.match(r"rg2x2-(\w+)-(\w+)-(\w+)$", scenario)
        if not m:
            continue
        _, arm, tier = m.groups()
        parsed = parse_stream(f)
        blob = " ".join(parsed["skill_inputs"]).lower()
        target = any(t in blob for t in TARGETS[bank])
        adjacent = any(t in blob for t in ADJACENT.get(bank, []))
        rows.append(
            {
                "bank": bank,
                "arm": arm,
                "tier": tier,
                "task": task,
                "repeat": repeat,
                "any_skill": bool(parsed["skill_inputs"]),
                "target": target,
                "adjacent": adjacent,
                "off_target": bool(parsed["skill_inputs"]) and not (target or adjacent),
                "gate_line": parsed["gate_line"],
                "footprint": footprint.get((bank, scenario, task, repeat)),
            }
        )

    if not rows:
        print("no parsable streams found")
        return 1

    def rate(sub, key):
        vals = [r[key] for r in sub if r[key] is not None]
        return f"{sum(vals)}/{len(vals)}" if vals else "-"

    print(f"trials parsed: {len(rows)}\n")
    for tier in TIERS:
        print(f"### tier={tier}  (pooled over {len(TARGETS)} banks)")
        print(
            f"{'arm':<6} {'target-act':>10} {'any-skill':>10} {'off-target':>10} "
            f"{'gate-line':>10} {'footprint':>10}"
        )
        for arm in ARMS:
            sub = [r for r in rows if r["tier"] == tier and r["arm"] == arm]
            print(
                f"{arm:<6} {rate(sub, 'target'):>10} {rate(sub, 'any_skill'):>10} "
                f"{rate(sub, 'off_target'):>10} {rate(sub, 'gate_line'):>10} "
                f"{rate(sub, 'footprint'):>10}"
            )
        print()

    print("### per-bank target activation")
    header = "bank".ljust(10) + "".join(f"{a}-{t:<6}" for t in TIERS for a in ARMS)
    print(header)
    for bank in TARGETS:
        cells = []
        for tier in TIERS:
            for arm in ARMS:
                sub = [
                    r for r in rows if r["bank"] == bank and r["tier"] == tier and r["arm"] == arm
                ]
                cells.append(rate(sub, "target").ljust(8))
        print(bank.ljust(10) + "".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())
