#!/usr/bin/env python3
"""humble-vs-super-v5: the pre-registered analysis, and the cumulative spend stop.

Two things fathom does not do for this bank, both load-bearing:

``spend``
    fathom has **no cumulative budget stop**. ``--max-budget-usd`` is a *per-spawn* cap
    passed through to the ``claude`` CLI, and ``_CEILING_PER_TRIAL_USD = 2.00`` is only
    the number ``--dry-run`` multiplies into the printed ceiling — nothing in the run loop
    halts on money already spent. The rail is therefore procedural: run in ``--limit N``
    chunks and call this between them. It sums ``cost_usd_est`` over ``kind == "run"``
    lines and exits **non-zero** once the stop threshold is reached, so it can gate a
    shell chain rather than relying on the operator reading a number.

``criteria``
    ``fathom report``'s Per-Criterion table pools each criterion **across tasks**
    (``src/fathom/report.py``). On this bank that blends the ceilinged
    ``fix-tz-dst-normalize`` with the only informative ``fix-offbyone-paginator`` into one
    figure — halving the visible gap, inflating apparent n, and on v1 vs v2 *flipping
    sign*. The pre-registered analysis is per **scenario x task x criterion**; this is it.

``cost``
    The economy axis, paired by task — the unit gate 3 pre-registers. Reports the
    per-cell means, the within-cell CV, and a paired t-test across tasks for each pair of
    arms.

Ledger lines carry no scenario on ``kind == "run"`` (economy joins after scoring, ADR-0003),
so run rows are attributed to an arm through ``config_hash``, which the ``kind == "trial"``
rows do carry.

Stdlib only; reads only, writes nothing. Runs without credentials and without uv:

    python scripts-humble-v5/analysis.py spend    ledger/humble-vs-super-v5.jsonl
    python scripts-humble-v5/analysis.py criteria ledger/humble-vs-super-v5.jsonl
    python scripts-humble-v5/analysis.py cost     ledger/humble-vs-super-v5.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Written stop rule for the v5 paid stage (V5_NOTES.md "The rails").
DEFAULT_STOP_USD = 150.0


# --------------------------------------------------------------------------- loading


def load_rows(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        if not path.is_file():
            sys.exit(f"no such ledger: {path}")
        with path.open(encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    sys.exit(f"{path}:{lineno}: malformed ledger line: {exc}")
    return rows


def scenario_by_config_hash(rows: list[dict]) -> dict[str, str]:
    """Map config_hash -> arm name, learned from the trial rows.

    Run rows omit the scenario on purpose (blindness); this is the documented join.
    """
    out: dict[str, str] = {}
    for r in rows:
        if r.get("kind") == "trial" and r.get("scenario") and r.get("config_hash"):
            out[r["config_hash"]] = r["scenario"]
    return out


def run_costs(rows: list[dict]) -> dict[tuple[str, str], list[float]]:
    """(arm, task_id) -> [cost_usd_est, ...] over completed run rows."""
    by_hash = scenario_by_config_hash(rows)
    out: dict[tuple[str, str], list[float]] = defaultdict(list)
    for r in rows:
        if r.get("kind") != "run":
            continue
        cost = r.get("cost_usd_est")
        if cost is None:
            continue
        arm = by_hash.get(r.get("config_hash", ""), "<unattributed>")
        out[(arm, r.get("task_id", "<none>"))].append(float(cost))
    return out


# ------------------------------------------------------------------------- statistics


def _betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta, Lentz continued fraction (NR 6.4). Stdlib only."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0

    def betacf(a: float, b: float, x: float) -> float:
        maxit, eps, fpmin = 300, 3e-16, 1e-300
        qab, qap, qam = a + b, a + 1.0, a - 1.0
        c = 1.0
        d = 1.0 - qab * x / qap
        d = fpmin if abs(d) < fpmin else d
        d = 1.0 / d
        h = d
        for m in range(1, maxit + 1):
            m2 = 2 * m
            aa = m * (b - m) * x / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            d = fpmin if abs(d) < fpmin else d
            c = 1.0 + aa / c
            c = fpmin if abs(c) < fpmin else c
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            d = fpmin if abs(d) < fpmin else d
            c = 1.0 + aa / c
            c = fpmin if abs(c) < fpmin else c
            d = 1.0 / d
            delta = d * c
            h *= delta
            if abs(delta - 1.0) < eps:
                break
        return h

    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * betacf(a, b, x) / a
    return 1.0 - front * betacf(b, a, 1.0 - x) / b


def t_test_two_sided_p(t_stat: float, df: int) -> float:
    """Two-sided p-value for Student's t. Returns 1.0 for a degenerate statistic."""
    if df <= 0 or not math.isfinite(t_stat):
        return 1.0
    return _betai(df / 2.0, 0.5, df / (df + t_stat * t_stat))


def paired_t(diffs: list[float]) -> tuple[float, float, float, int, float]:
    """(mean, sd, t, df, p) for a paired sample. Degenerate samples return p = 1.0."""
    n = len(diffs)
    if n < 2:
        return (statistics.fmean(diffs) if diffs else 0.0, 0.0, 0.0, 0, 1.0)
    mean = statistics.fmean(diffs)
    sd = statistics.stdev(diffs)
    if sd == 0.0:
        return (mean, 0.0, math.inf if mean else 0.0, n - 1, 0.0 if mean else 1.0)
    t_stat = mean / (sd / math.sqrt(n))
    return (mean, sd, t_stat, n - 1, t_test_two_sided_p(t_stat, n - 1))


# ---------------------------------------------------------------------- subcommands


def cmd_spend(args: argparse.Namespace) -> int:
    rows = load_rows(args.ledger)
    costs = [
        float(r["cost_usd_est"])
        for r in rows
        if r.get("kind") == "run" and r.get("cost_usd_est") is not None
    ]
    total = sum(costs)
    by_arm: dict[str, float] = defaultdict(float)
    for (arm, _task), vals in run_costs(rows).items():
        by_arm[arm] += sum(vals)

    completed = sum(1 for r in rows if r.get("kind") == "trial" and r.get("status") == "completed")
    print(f"trials with cost: {len(costs)}   completed trials: {completed}")
    for arm in sorted(by_arm):
        print(f"  {arm:<16} ${by_arm[arm]:.2f}")
    print(f"CUMULATIVE SPEND: ${total:.2f}   stop rule: ${args.stop_usd:.2f}")
    if costs:
        print(f"  mean ${statistics.fmean(costs):.4f}/trial   max ${max(costs):.4f}")

    if total >= args.stop_usd:
        print(
            f"\nSTOP: cumulative ${total:.2f} has reached the ${args.stop_usd:.2f} rail. "
            "Do not re-invoke `fathom run`. The resume key makes stopping free.",
            file=sys.stderr,
        )
        return 2
    print(f"  headroom to rail: ${args.stop_usd - total:.2f}")
    return 0


def cmd_criteria(args: argparse.Namespace) -> int:
    rows = load_rows(args.ledger)
    counts: dict[tuple[str, str, str], list[int]] = defaultdict(lambda: [0, 0])
    for r in rows:
        if r.get("kind") != "trial" or r.get("status") != "completed":
            continue
        if r.get("infra_error"):
            continue
        results = r.get("verifier_results")
        if not isinstance(results, dict):
            continue
        for crit, val in results.items():
            key = (r.get("task_id", "<none>"), crit, r.get("scenario", "<none>"))
            counts[key][1] += 1
            if val:
                counts[key][0] += 1

    if not counts:
        print("no completed trials with verifier results yet")
        return 0

    arms = sorted({k[2] for k in counts})
    width = max(len(f"{t}/{c}") for t, c, _ in counts) + 2

    print("PER-TASK per-criterion pass rates (the pre-registered analysis).")
    print("`fathom report` pools these ACROSS tasks; that pooled row is not the analysis.\n")
    header = f"{'task':<24} {'criterion':<26}" + "".join(
        f"{a:>{max(width, len(a) + 2)}}" for a in arms
    )
    print(header)
    print("-" * len(header))

    last_task = None
    for task, crit in sorted({(k[0], k[1]) for k in counts}):
        if last_task is not None and task != last_task:
            print()
        last_task = task
        cells = []
        saturated = True
        for arm in arms:
            passed, total = counts.get((task, crit, arm), [0, 0])
            cells.append(f"{passed}/{total}" if total else "-")
            if total and passed != total:
                saturated = False
        row = f"{task:<24} {crit:<26}" + "".join(
            f"{c:>{max(width, len(a) + 2)}}" for c, a in zip(cells, arms)
        )
        print(row + ("" if saturated else "   <-- headroom"))
    return 0


def cmd_cost(args: argparse.Namespace) -> int:
    rows = load_rows(args.ledger)
    costs = run_costs(rows)
    if not costs:
        print("no run rows with cost yet")
        return 0

    arms = sorted({a for a, _ in costs})
    tasks = sorted({t for _, t in costs})

    print("Per-cell cost (arm x task): n, mean USD, within-cell CV\n")
    cvs = []
    for arm in arms:
        for task in tasks:
            vals = costs.get((arm, task))
            if not vals:
                continue
            mean = statistics.fmean(vals)
            sd = statistics.stdev(vals) if len(vals) > 1 else 0.0
            cv = 100 * sd / mean if mean else 0.0
            if len(vals) > 1:
                cvs.append(cv)
            print(f"  {arm:<16} {task:<24} n={len(vals):<3} ${mean:.4f}  cv={cv:.1f}%")
    if cvs:
        print(f"\n  median within-cell CV: {statistics.median(cvs):.1f}%")

    print("\nPAIRED-BY-TASK cost test (gate 3). Unit = task; one pair per task.")
    print("Rule: separation at p < 0.05 answers the economy question — do not buy the fill.\n")
    for i, a in enumerate(arms):
        for b in arms[i + 1 :]:
            shared = [t for t in tasks if costs.get((a, t)) and costs.get((b, t))]
            if len(shared) < 2:
                print(f"  {a} vs {b}: only {len(shared)} shared task(s) — not testable yet")
                continue
            diffs_pct = []
            for task in shared:
                ma = statistics.fmean(costs[(a, task)])
                mb = statistics.fmean(costs[(b, task)])
                diffs_pct.append(100 * (mb - ma) / ma if ma else 0.0)
            mean, sd, t_stat, df, p = paired_t(diffs_pct)
            verdict = "SEPARATED (p<0.05)" if p < 0.05 else "not separated"
            print(f"  {a} -> {b} over {len(shared)} tasks:")
            for task, d in zip(shared, diffs_pct):
                print(f"      {task:<24} {d:+.1f}%")
            print(
                f"      mean {mean:+.1f}%  sd {sd:.1f}  t={t_stat:.2f}  df={df}  "
                f"p={p:.4f}  -> {verdict}\n"
            )
    return 0


# ----------------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "humble-vs-super-v5 pre-registered analysis and cumulative spend stop. "
            "fathom has no cumulative budget rail; `spend` is it."
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func, helptext in (
        ("spend", cmd_spend, "cumulative USD from the ledger; exits 2 at the stop rule"),
        ("criteria", cmd_criteria, "pass rates per scenario x task x criterion"),
        ("cost", cmd_cost, "per-cell economy plus the paired-by-task test (gate 3)"),
    ):
        p = sub.add_parser(name, help=helptext, description=helptext)
        p.add_argument("ledger", nargs="+", type=Path, help="ledger .jsonl path(s)")
        p.set_defaults(func=func)
        if name == "spend":
            p.add_argument(
                "--stop-usd",
                type=float,
                default=DEFAULT_STOP_USD,
                help=f"cumulative rail; exit 2 at or above it (default {DEFAULT_STOP_USD})",
            )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
