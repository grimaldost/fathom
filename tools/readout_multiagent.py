"""Readout for the multiagent-composition bank — the pre-registered analysis, and only that.

Written before the pilot's first trial completed, so the analysis is fixed while the data
is not. It computes exactly what docs/specs/2026-09-01-multiagent-composition-preregistration.md
declares (plus addendum #4's sensitivity endpoint and #5's dose counts) and refuses to
compute anything else. Any reading outside this script is exploratory and must say so.

    uv run python tools/readout_multiagent.py [--ledger ledger/multiagent-composition.jsonl]
                                              [--streams streams-multiagent/<dir>]

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from math import comb
from pathlib import Path

from fathom.ledger import apply_voids

HELD_OUT = (
    "type_bool_arith_heldout",
    "type_compare_heldout",
    "env_bool_typing",
    "not_precedence_heldout",
    "error_type_is_typemismatch",
    "short_circuit_heldout",
)
# Addendum #4: the four held-out criteria the probes' rule does not touch.
HELD_OUT_INDEPENDENT = (
    "env_bool_typing",
    "not_precedence_heldout",
    "error_type_is_typemismatch",
    "short_circuit_heldout",
)
ARMS = ("control", "placebo", "perpr", "final")
TIERS = ("haiku", "sonnet")
# The four pre-registered contrasts, one-sided treatment > control, Holm within tier-set.
CONTRASTS = (("perpr", "control"), ("perpr", "placebo"), ("final", "control"), ("final", "placebo"))
DRIVER_MARKER = "run_convoy_gate.py"
PLACEBO_MARKER = "transient check failed"


def fisher_greater(x: int, nx: int, y: int, ny: int) -> float:
    """One-sided Fisher exact: P(X >= x) under the hypergeometric null."""
    a, b, c, d = x, nx - x, y, ny - y
    n, r1, c1 = a + b + c + d, a + b, a + c
    if n == 0:
        return 1.0
    tot = comb(n, c1)
    return sum(comb(r1, i) * comb(n - r1, c1 - i) for i in range(a, min(r1, c1) + 1)) / tot


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def holm(pvals: dict[str, float]) -> dict[str, float]:
    """Holm step-down adjusted p-values over one family."""
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for rank, (name, p) in enumerate(items):
        val = min(1.0, (m - rank) * p)
        running = max(running, val)
        adjusted[name] = running
    return adjusted


def split_scenario(name: str) -> tuple[str, str] | None:
    for arm in ARMS:
        for tier in TIERS:
            if name == f"{arm}-{tier}":
                return arm, tier
    return None


def load(ledger: Path) -> tuple[list[dict], list[dict]]:
    rows = [
        json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    # Voided trials and their runs are excluded as of the void row; a re-run counts.
    rows = apply_voids(rows)
    trials = [r for r in rows if r.get("kind") == "trial" and split_scenario(r.get("scenario", ""))]
    runs = [r for r in rows if r.get("kind") == "run"]
    return trials, runs


def gate_counts(detail: str) -> tuple[int | None, int | None]:
    """(first-gate reds, fix rounds) from a gated-session detail line, else (None, None)."""
    if not detail or "gate first=" not in detail:
        return None, None
    first_red = 1 if "first=red" in detail else 0
    fixes = None
    for token in detail.split():
        if token.startswith("fixes="):
            try:
                fixes = int(token[len("fixes=") :].rstrip(";,"))
            except ValueError:
                pass
    return first_red, fixes


def per_trial_cost(runs: list[dict]) -> dict[tuple[str, int], float]:
    cost: dict[tuple[str, int], float] = defaultdict(float)
    for r in runs:
        if r.get("cost_usd_est"):
            cost[(r["config_hash"], r.get("repeat", -1))] += float(r["cost_usd_est"])
    return cost


def per_trial_duration(runs: list[dict]) -> dict[tuple[str, int], float]:
    """Wall-clock per trial: the sum of its run rows' ``duration`` (trial rows carry none)."""
    dur: dict[tuple[str, int], float] = defaultdict(float)
    for r in runs:
        if r.get("duration"):
            dur[(r["config_hash"], r.get("repeat", -1))] += float(r["duration"])
    return dur


def transcripts_by_trial(streams: Path | None) -> dict[str, list[str]]:
    """Raw transcript text keyed by the stream tag prefix (before '--a')."""
    out: dict[str, list[str]] = defaultdict(list)
    if not streams or not streams.is_dir():
        return out
    for f in streams.glob("*.ndjson"):
        tag = f.name.split("--a")[0]
        out[tag].append(f.read_text(encoding="utf-8", errors="replace"))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", default="ledger/multiagent-composition.jsonl")
    ap.add_argument("--streams", default=None)
    args = ap.parse_args(argv)

    trials, runs = load(Path(args.ledger))
    cost = per_trial_cost(runs)
    dur = per_trial_duration(runs)
    streams = transcripts_by_trial(Path(args.streams)) if args.streams else {}

    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in trials:
        arm, tier = split_scenario(t["scenario"])
        cells[(arm, tier)].append(t)

    print("multiagent-composition readout — pre-registered endpoints only")
    print(
        f"trials: {len(trials)}  (completed: {sum(1 for t in trials if t.get('status') == 'completed')})"
    )
    print()
    hdr = f"{'cell':16} {'n':>2} {'held_out':>9} {'ho_indep':>9} {'full15':>7} {'1st-red':>7} {'fixes':>6} {'$/trial':>8} {'wall_s':>7}"
    print(hdr)
    stats: dict[tuple[str, str], dict] = {}
    for tier in TIERS:
        for arm in ARMS:
            ts = [t for t in cells.get((arm, tier), []) if t.get("status") == "completed"]
            n = len(ts)
            ho = sum(1 for t in ts if all(t.get("verifier_results", {}).get(c) for c in HELD_OUT))
            hoi = sum(
                1
                for t in ts
                if all(t.get("verifier_results", {}).get(c) for c in HELD_OUT_INDEPENDENT)
            )
            full = sum(
                1
                for t in ts
                if all(v for k, v in t.get("verifier_results", {}).items() if k not in HELD_OUT)
            )
            reds, fixes = [], []
            for t in ts:
                fr, fx = gate_counts(t.get("detail") or "")
                if fr is not None:
                    reds.append(fr)
                if fx is not None:
                    fixes.append(fx)
            costs = [
                cost[(t["config_hash"], t.get("repeat", -1))]
                for t in ts
                if (t["config_hash"], t.get("repeat", -1)) in cost
            ]
            walls = [
                dur[(t["config_hash"], t.get("repeat", -1))]
                for t in ts
                if (t["config_hash"], t.get("repeat", -1)) in dur
            ]
            stats[(arm, tier)] = {"n": n, "ho": ho, "hoi": hoi, "full": full}
            print(
                f"{arm + '-' + tier:16} {n:>2} {ho:>4}/{n:<4} {hoi:>4}/{n:<4} {full:>3}/{n:<3} "
                f"{(sum(reds) if reds else '-'):>7} {(sum(fixes) if fixes else '-'):>6} "
                f"{(f'{statistics.median(costs):.2f}' if costs else '-'):>8} "
                f"{(f'{statistics.median(walls):.0f}' if walls else '-'):>7}"
            )
    print()
    print("Wilson 95% on held_out_clean:")
    for (arm, tier), s in stats.items():
        lo, hi = wilson(s["ho"], s["n"])
        print(f"  {arm + '-' + tier:16} {s['ho']}/{s['n']}  [{lo:.2f}, {hi:.2f}]")
    print()
    for endpoint, key in (
        ("PRIMARY held_out_clean", "ho"),
        ("SENSITIVITY held_out_clean_independent (not in the Holm family)", "hoi"),
    ):
        print(endpoint)
        for tier in TIERS:
            raw: dict[str, float] = {}
            for treat, ctrl in CONTRASTS:
                a, b = stats.get((treat, tier)), stats.get((ctrl, tier))
                if not a or not b or a["n"] == 0 or b["n"] == 0:
                    continue
                raw[f"{treat} vs {ctrl}"] = fisher_greater(a[key], a["n"], b[key], b["n"])
            adj = holm(raw) if key == "ho" else {}
            for name, p in raw.items():
                treat, ctrl = name.split(" vs ")
                a, b = stats[(treat, tier)], stats[(ctrl, tier)]
                line = f"  [{tier}] {name:18} {a[key]}/{a['n']} vs {b[key]}/{b['n']}  one-sided p={p:.4f}"
                if adj:
                    line += f"  Holm p={adj[name]:.4f}"
                print(line)
        print()

    print("ARMING (pre-registered pilot criteria) + mechanism attestation from transcripts:")
    if streams:
        import re

        dated = re.compile(r'"model":\s*"(claude-[a-z0-9-]+-20\d{6})"')
        agent_marker = '"name":"Agent"'
        for tag, texts in sorted(streams.items()):
            blob = "\n".join(texts)
            found = sorted({m.split("claude-", 1)[1] for m in dated.findall(blob)})
            # Sonnet events carry only the undated alias, so its snapshot is NOT pinnable
            # from transcripts; say so rather than print an empty field.
            models = ",".join(found) if found else "undated-alias-only"
            short = tag.replace("multiagent-composition--", "").replace("--exprlang", "")
            print(
                f"  {short:24} agent_dispatches={blob.count(agent_marker):>2}  "
                f"driver={blob.count(DRIVER_MARKER):>2}  "
                f"placebo={'y' if PLACEBO_MARKER in blob else 'n'}  models={models}"
            )
    else:
        print("  (no --streams given: perpr invocation counts and placebo firing are NOT attested)")
    finals = [t for t in trials if split_scenario(t["scenario"])[0] == "final"]
    attested = sum(1 for t in finals if "convoy gate via:" in (t.get("detail") or ""))
    print(f"  final-* rows carrying the convoy provenance line in detail: {attested}/{len(finals)}")
    print()
    print("NOTE: the pilot draws no inference (pre-registration, Endpoints). The p-values above")
    print("are printed so the main-matrix power calculation and its addendum can cite them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
