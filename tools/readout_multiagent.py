"""Readout for the multiagent-composition bank — the pre-registered analysis, and only that.

Written before the pilot's first trial completed, so the analysis is fixed while the data
is not. It computes exactly what docs/specs/2026-09-01-multiagent-composition-preregistration.md
declares (plus addendum #4's sensitivity endpoint and #5's dose counts) and refuses to
compute anything else. Any reading outside this script is exploratory and must say so.

    uv run python tools/readout_multiagent.py [--ledger ledger/multiagent-composition.jsonl]
                                              [--streams streams-multiagent/<dir>]
                                              [--family iter1|iter2]

``--family iter2`` reads the 2026-09 iteration-2 arms (control2 / placebo2 / perpr2 / hook2)
with their own Holm family of four, and prints — outside that family and labelled as such —
the hook2-vs-perpr2 two-sided contrast with a Newcombe interval, placebo2-vs-control2, and
a cost / wall-clock / orchestrator-turns block with Mann-Whitney U. ``iter1`` (the default)
is the original readout, unchanged.

Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from math import comb, erfc
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
ARMS = ("control", "placebo", "perpr", "final", "hook")
TIERS = ("haiku", "sonnet")
# The four pre-registered contrasts, one-sided treatment > control, Holm within tier-set.
CONTRASTS = (("perpr", "control"), ("perpr", "placebo"), ("final", "control"), ("final", "placebo"))
# Iteration 2 (2026-09): eight new contemporaneous cells on the same bank and fixture.
ITER2_ARMS = ("control2", "placebo2", "perpr2", "hook2")
ITER2_CONTRASTS = (
    ("hook2", "control2"),
    ("hook2", "placebo2"),
    ("perpr2", "placebo2"),
    ("perpr2", "control2"),
)
FAMILIES = {
    "iter1": {
        "arms": ARMS,
        "contrasts": CONTRASTS,
        "ledger": "ledger/multiagent-composition.jsonl",
    },
    "iter2": {
        "arms": ITER2_ARMS,
        "contrasts": ITER2_CONTRASTS,
        "ledger": "ledger/multiagent-composition-v2.jsonl",
    },
}
# Outside the Holm family (iter2): the treatment-vs-treatment contrast and the placebo check.
ITER2_HOOK_VS_PERPR = ("hook2", "perpr2")
ITER2_PLACEBO_VS_CONTROL = ("placebo2", "control2")
ITER2_ECONOMY_CONTRASTS = (("hook2", "perpr2"), ("hook2", "control2"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stream_facts  # noqa: E402

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


def fisher_two_sided(x: int, nx: int, y: int, ny: int) -> float:
    """Two-sided Fisher exact: the mass of every table no more probable than the observed."""
    r1, c1, n = nx, x + y, nx + ny
    if n == 0:
        return 1.0
    lo, hi = max(0, c1 - (n - r1)), min(r1, c1)
    weights = {i: comb(r1, i) * comb(n - r1, c1 - i) for i in range(lo, hi + 1)}
    observed = weights[x]
    return sum(w for w in weights.values() if w <= observed) / comb(n, c1)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe(k1: int, n1: int, k2: int, n2: int, z: float = 1.96) -> tuple[float, float, float]:
    """(p1 - p2, lower, upper): Newcombe's hybrid Wilson score interval (method 10, 1998)."""
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1, z)
    l2, u2 = wilson(k2, n2, z)
    d = p1 - p2
    lo = d - ((p1 - l1) ** 2 + (u2 - p2) ** 2) ** 0.5
    hi = d + ((u1 - p1) ** 2 + (p2 - l2) ** 2) ** 0.5
    return d, lo, hi


def _u_counts(m: int, n: int) -> list[int]:
    """Frequency of each U = 0..m*n under H0 without ties (f(m,n,u) = f(m-1,n,u-n) + f(m,n-1,u))."""
    table: dict[tuple[int, int], list[int]] = {}
    for i in range(m + 1):
        for j in range(n + 1):
            if i == 0 or j == 0:
                table[(i, j)] = [1]
                continue
            out = [0] * (i * j + 1)
            for u, c in enumerate(table[(i - 1, j)]):  # the largest value is an x: +j pairs
                out[u + j] += c
            for u, c in enumerate(table[(i, j - 1)]):  # the largest value is a y: +0
                out[u] += c
            table[(i, j)] = out
    return table[(m, n)]


def mann_whitney(x: list[float], y: list[float]) -> tuple[float, float, str]:
    """(U for x, two-sided p, method): exact without ties, else normal with tie correction."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float("nan"), 1.0, "n/a"
    pooled = sorted([(v, 0) for v in x] + [(v, 1) for v in y], key=lambda t: t[0])
    ranks = [0.0] * len(pooled)
    ties: list[int] = []
    i = 0
    while i < len(pooled):
        j = i
        while j + 1 < len(pooled) and pooled[j + 1][0] == pooled[i][0]:
            j += 1
        for k in range(i, j + 1):
            ranks[k] = (i + j + 2) / 2  # 1-based ranks i+1..j+1 averaged
        if j > i:
            ties.append(j - i + 1)
        i = j + 1
    r1 = sum(r for r, (_, g) in zip(ranks, pooled) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    u = min(u1, n1 * n2 - u1)
    if not ties:
        counts = _u_counts(n1, n2)
        p = 2 * sum(counts[: int(u) + 1]) / comb(n1 + n2, n1)
        return u1, min(1.0, p), "exact"
    big_n = n1 + n2
    tie_term = sum(t**3 - t for t in ties) / (big_n * (big_n - 1))
    sigma = (n1 * n2 / 12 * ((big_n + 1) - tie_term)) ** 0.5
    if sigma == 0:
        return u1, 1.0, "normal (all tied)"
    z = (u - n1 * n2 / 2 + 0.5) / sigma  # continuity-corrected, u is the smaller U so z <= 0
    p = erfc(-z / 2**0.5)  # 2 * Phi(z)
    return u1, min(1.0, p), "normal, tie-corrected"


def median_iqr(xs: list[float]) -> tuple[float, float, float]:
    """(median, Q1, Q3); the quartiles are the inclusive (linear) ones."""
    if len(xs) < 2:
        v = xs[0] if xs else float("nan")
        return v, v, v
    q1, med, q3 = statistics.quantiles(xs, n=4, method="inclusive")
    return med, q1, q3


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


def split_scenario(name: str, arms: tuple[str, ...] = ARMS) -> tuple[str, str] | None:
    """(arm, tier) for a scenario named ``<arm>-<tier>`` over *arms*; split on the last '-'."""
    if "-" not in name:
        return None
    arm, tier = name.rsplit("-", 1)
    if arm in arms and tier in TIERS:
        return arm, tier
    return None


def load(ledger: Path, arms: tuple[str, ...] = ARMS) -> tuple[list[dict], list[dict]]:
    rows = [
        json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    # Voided trials and their runs are excluded as of the void row; a re-run counts.
    rows = apply_voids(rows)
    trials = [
        r for r in rows if r.get("kind") == "trial" and split_scenario(r.get("scenario", ""), arms)
    ]
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


def per_trial_turns(runs: list[dict]) -> dict[tuple[str, int], int]:
    """Orchestrator turns per trial: the sum of its run rows' ``turns``."""
    turns: dict[tuple[str, int], int] = defaultdict(int)
    for r in runs:
        if r.get("turns") is not None:
            turns[(r["config_hash"], r.get("repeat", -1))] += int(r["turns"])
    return turns


def _fmt_iqr(xs: list[float], digits: int) -> str:
    if not xs:
        return "-"
    med, q1, q3 = median_iqr(xs)
    return f"{med:.{digits}f} [{q1:.{digits}f}, {q3:.{digits}f}]"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--ledger",
        default=None,
        help="defaults to the family's own ledger (see FAMILIES); always pass explicitly "
        "for anything other than the default family's canonical ledger",
    )
    ap.add_argument("--streams", action="append", default=None, help="repeatable")
    ap.add_argument("--task-dir-name", default=None, help="defaults to the ledger stem")
    ap.add_argument(
        "--family",
        choices=sorted(FAMILIES),
        default="iter1",
        help="which arm family to read out (iter1: the original arms; iter2: the *2 arms)",
    )
    args = ap.parse_args(argv)
    arms: tuple[str, ...] = FAMILIES[args.family]["arms"]
    contrasts: tuple[tuple[str, str], ...] = FAMILIES[args.family]["contrasts"]
    if args.ledger is None:
        args.ledger = FAMILIES[args.family]["ledger"]

    trials, runs = load(Path(args.ledger), arms)
    cost = per_trial_cost(runs)
    dur = per_trial_duration(runs)
    turns = per_trial_turns(runs)
    stream_dirs = [Path(s) for s in args.streams] if args.streams else []
    task_dir_name = args.task_dir_name or Path(args.ledger).stem

    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for t in trials:
        arm, tier = split_scenario(t["scenario"], arms)
        cells[(arm, tier)].append(t)

    print(
        "multiagent-composition readout — pre-registered endpoints only"
        + ("" if args.family == "iter1" else f"  [family: {args.family}]")
    )
    print(
        f"trials: {len(trials)}  (completed: {sum(1 for t in trials if t.get('status') == 'completed')})"
    )
    print()
    hdr = f"{'cell':16} {'n':>2} {'held_out':>9} {'ho_indep':>9} {'full15':>7} {'1st-red':>7} {'fixes':>6} {'med$/tr':>8} {'med_s':>7}"
    print(hdr)
    stats: dict[tuple[str, str], dict] = {}
    for tier in TIERS:
        for arm in arms:
            ts = [t for t in cells.get((arm, tier), []) if t.get("status") == "completed"]
            n = len(ts)
            if n == 0:
                continue  # an arm pre-registered on this bank but not bought in this matrix
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
            turn_counts = [
                turns[(t["config_hash"], t.get("repeat", -1))]
                for t in ts
                if (t["config_hash"], t.get("repeat", -1)) in turns
            ]
            stats[(arm, tier)] = {
                "n": n,
                "ho": ho,
                "hoi": hoi,
                "full": full,
                "costs": costs,
                "walls": walls,
                "turns": turn_counts,
            }
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
    # held_out_clean_independent is iteration 1's addendum-4 sensitivity endpoint, ruled
    # inconclusive by the 2026-09-03 blind review; iteration 2's pre-registration and typed
    # record declare exactly two outcomes (held_out_clean, full15_clean) and do not declare
    # this one, so it is shown only for the iter1 family, never as an iter2 endpoint.
    endpoints: list[tuple[str, str]] = [("PRIMARY held_out_clean", "ho")]
    if args.family == "iter1":
        endpoints.append(("SENSITIVITY held_out_clean_independent (not in the Holm family)", "hoi"))
    for endpoint, key in endpoints:
        print(endpoint)
        for tier in TIERS:
            raw: dict[str, float] = {}
            for treat, ctrl in contrasts:
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

    if args.family == "iter2":
        _print_iter2_extras(stats)

    print("ARMING (pre-registered pilot criteria) + mechanism attestation from transcripts")
    print(
        "  (tool_use events on the surviving stream of each counted trial; tools/stream_facts.py)"
    )
    if stream_dirs:
        facts = stream_facts.all_facts(Path(args.ledger), stream_dirs, task_dir_name)
        for (scenario, repeat), f in facts.items():
            models = ",".join(sorted(f.models)) or "undated-alias-only"
            hook = f"{f.hook_log_firings}/{f.hook_log_stops}" if f.hook_log_present else "-"
            print(
                f"  {scenario:16} r{repeat:<3} dispatches={f.agent_dispatches:>2} "
                f"driver={f.driver_calls:>2} reds={f.driver_reds} "
                f"placebo={f.placebo_calls}/{f.placebo_reds} spawn_driver={f.spawn_driver_calls} "
                f"hook={hook:5} exposed={len(f.exposure):>2} models={models}"
            )
        print()
        print(
            "DOSE (pre-registration addendum 5): gate reds and fix dispatches per trial, per cell"
        )
        print("\n".join(stream_facts.dose_table(facts)))
        exposed = sorted(k for k, f in facts.items() if f.exposure)
        print()
        print(
            f"EXPOSURE: {len(exposed)} counted trial(s) touched the task dir outside prompts/: "
            + (", ".join(f"{s} r{r}" for s, r in exposed) or "none")
        )
    else:
        print("  (no --streams given: dose, dispatches and exposure are NOT attested)")
    if "final" in arms:
        finals = [t for t in trials if split_scenario(t["scenario"], arms)[0] == "final"]
        attested = sum(1 for t in finals if "convoy gate via:" in (t.get("detail") or ""))
        print(
            f"  final-* rows carrying the convoy provenance line in detail: {attested}/{len(finals)} "
            "(the line is recorded only when the last gate round completed green: a logging "
            "consequence of the verdict, not evidence of which binary ran)"
        )
    print()
    if all(s["n"] <= 3 for s in stats.values()):
        print(
            "NOTE: the pilot draws no inference (pre-registration, Endpoints). The p-values above"
        )
        print("are printed so the main-matrix power calculation and its addendum can cite them.")
    return 0


def _print_iter2_extras(stats: dict[tuple[str, str], dict]) -> None:
    """The iteration-2 readings that sit OUTSIDE the Holm family, labelled as such."""
    print("OUTSIDE THE HOLM FAMILY (iteration 2; exploratory, not multiplicity-adjusted)")
    print("  held_out_clean, treatment vs treatment and the placebo check:")
    for tier in TIERS:
        a, b = stats.get((ITER2_HOOK_VS_PERPR[0], tier)), stats.get((ITER2_HOOK_VS_PERPR[1], tier))
        if a and b:
            p = fisher_two_sided(a["ho"], a["n"], b["ho"], b["n"])
            d, lo, hi = newcombe(a["ho"], a["n"], b["ho"], b["n"])
            print(
                f"  [{tier}] {ITER2_HOOK_VS_PERPR[0]} vs {ITER2_HOOK_VS_PERPR[1]:9} "
                f"{a['ho']}/{a['n']} vs {b['ho']}/{b['n']}  two-sided Fisher p={p:.4f}  "
                f"diff={d:+.3f}  Newcombe 95% [{lo:+.3f}, {hi:+.3f}]"
            )
        a, b = (
            stats.get((ITER2_PLACEBO_VS_CONTROL[0], tier)),
            stats.get((ITER2_PLACEBO_VS_CONTROL[1], tier)),
        )
        if a and b:
            p = fisher_greater(a["ho"], a["n"], b["ho"], b["n"])
            print(
                f"  [{tier}] {ITER2_PLACEBO_VS_CONTROL[0]} vs {ITER2_PLACEBO_VS_CONTROL[1]:9} "
                f"{a['ho']}/{a['n']} vs {b['ho']}/{b['n']}  one-sided p={p:.4f}"
            )
    print()
    print("COST / WALL-CLOCK / ORCHESTRATOR TURNS per trial (median [Q1, Q3], inclusive quartiles)")
    print(f"  {'cell':16} {'n':>2}  {'cost $/trial':24} {'wall-clock s':24} {'turns':20}")
    for tier in TIERS:
        for arm in ITER2_ARMS:
            s = stats.get((arm, tier))
            if not s:
                continue
            print(
                f"  {arm + '-' + tier:16} {s['n']:>2}  {_fmt_iqr(s['costs'], 2):24} "
                f"{_fmt_iqr(s['walls'], 0):24} {_fmt_iqr(s['turns'], 0):20}"
            )
    print()
    print(
        "COST PER HELD-OUT-CLEAN TRIAL (cell spend over clean trials; dash when ho == 0, "
        "descriptive)"
    )
    for tier in TIERS:
        for arm in ITER2_ARMS:
            s = stats.get((arm, tier))
            if not s:
                continue
            per_clean = f"{sum(s['costs']) / s['ho']:.2f}" if s["ho"] else "-"
            print(
                f"  {arm + '-' + tier:16} spend=${sum(s['costs']):.2f}  ho={s['ho']}  ${per_clean}/clean"
            )
    print("  Mann-Whitney U, two-sided (exact when no ties; else normal, tie-corrected):")
    for tier in TIERS:
        for treat, ctrl in ITER2_ECONOMY_CONTRASTS:
            a, b = stats.get((treat, tier)), stats.get((ctrl, tier))
            if not a or not b:
                continue
            parts = []
            for metric in ("costs", "turns"):
                xs, ys = a[metric], b[metric]
                if not xs or not ys:
                    parts.append(f"{metric}: -")
                    continue
                u, p, method = mann_whitney(xs, ys)
                parts.append(f"{metric}: U={u:.1f} p={p:.4f} ({method})")
            print(f"  [{tier}] {treat} vs {ctrl:9} n={a['n']}/{b['n']}  " + "  ".join(parts))
    print()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
