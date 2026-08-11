"""Analyse the three-arm vNext contrast: bare vs skill vs skill-vnext.

Extends `analyse_map.py` from two arms to three. The added arm injects the
*shipped* vNext body (craft-collection `evals/arms/verification-vnext/`), so the
`skill-vnext` - `skill` contrast is the body diff alone: same delegation
preamble, same framing line, same model, effort, tools and limits.

Every contrast is computed on tasks scored in ALL arms present, because the arms
run the same tasks and the paired test is the one the design licenses. Emits per
(tier, class, criterion): the arm rates with Wilson intervals, each pairwise lift
with a Newcombe interval, and the exact McNemar p on the discordant pairs.

Non-inferiority is decided against a pre-declared margin (NI_MARGIN_PP), one
sided, on the Newcombe lower bound -- and the achieved half-width is printed
beside it so an interval too wide to decide is reported as such rather than
read as a pass.

Stdlib only. Free -- reads the ledger, spawns nothing.

    uv run python tasks/verif-lift-authoring/analyse_vnext.py
"""

from __future__ import annotations

import json
import math
import pathlib
import sys
from collections import defaultdict

# The report tables carry en-dashes and minus signs; a cp1252 console would
# otherwise kill the run mid-table with a UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

LEDGER = pathlib.Path("ledger")
ARMS = ("bare", "skill", "skill-vnext")

# Pre-declared before the spend: vNext is non-inferior on a criterion when the
# 95% Newcombe lower bound of (skill-vnext - skill) sits above -10 pp.
NI_MARGIN_PP = -10.0

BLOCKS = [
    ("verif-lift-bug-v1", "weak", "BUG"),
    ("verif-lift-data-v1", "weak", "DATA"),
    ("verif-lift-trunc-v1", "weak", "TRUNC"),
    ("verif-lift-null-v1", "weak", "NULL"),
    ("verif-lift-bug-strong-v1", "strong", "BUG"),
    ("verif-lift-data-strong-v1", "strong", "DATA"),
]

PRIMARY = {
    "BUG": "regression_check_present",
    "DATA": "regression_check_present",
    "TRUNC": "defect_past_slice_handled",
    "NULL": "scope_respected",
}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    ph = k / n
    d = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / d
    half = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float]:
    """Newcombe score interval for p2 - p1 (arm2 minus arm1)."""
    if n1 == 0 or n2 == 0:
        return (0.0, 0.0)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return (max(-1.0, lo), min(1.0, hi))


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5**n)
    return min(1.0, 2 * tail)


def mdd_pp(n: int) -> float:
    """Minimum detectable difference: the discordant split at n that McNemar
    would call at p<0.05, expressed in points of the paired rate."""
    for d in range(1, n + 1):
        if mcnemar_exact(0, d) < 0.05:
            return d / n * 100
    return 100.0


def load(bank: str) -> tuple[list[dict], list[dict]]:
    path = LEDGER / f"{bank}.jsonl"
    trials: list[dict] = []
    runs: list[dict] = []
    if not path.exists():
        return trials, runs
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("kind") == "trial" and rec.get("scenario") in ARMS:
            if not rec.get("holdout", False):
                trials.append(rec)
        elif rec.get("kind") == "run":
            runs.append(rec)
    return trials, runs


def main() -> None:
    hash_to_arm: dict[str, str] = {}
    hash_to_block: dict[str, tuple[str, str]] = {}

    print("# verification-lift vNext — three-arm per-cell contrast (n=1)\n")
    print(f"Arms: {', '.join(ARMS)}.  Non-inferiority margin: {NI_MARGIN_PP:+.0f} pp ")
    print("(pre-declared; one-sided on the Newcombe lower bound of skill-vnext − skill).\n")

    all_cells: list[dict] = []
    for bank, tier, klass in BLOCKS:
        trials, runs = load(bank)
        if not trials:
            print(f"## {tier}/{klass} ({bank}) — NO TRIALS IN LEDGER\n")
            continue

        by_arm: dict[str, dict[str, dict]] = defaultdict(dict)
        errored: dict[str, int] = defaultdict(int)
        for t in trials:
            hash_to_arm[t["config_hash"]] = t["scenario"]
            hash_to_block[t["config_hash"]] = (tier, klass)
            if t.get("status") != "completed":
                errored[t["scenario"]] += 1
                continue
            by_arm[t["scenario"]][t["task_id"]] = t.get("verifier_results") or {}

        present = [a for a in ARMS if by_arm.get(a)]
        if len(present) < 2:
            print(f"## {tier}/{klass} ({bank}) — only arm(s) {present}; no contrast\n")
            continue

        common = set(by_arm[present[0]])
        for a in present[1:]:
            common &= set(by_arm[a])
        tasks = sorted(common)
        n = len(tasks)

        criteria: set[str] = set()
        for a in present:
            for res in by_arm[a].values():
                criteria.update(res)

        counts = {a: len(by_arm[a]) for a in present}
        print(f"## {tier} / {klass}  ({bank})")
        print(
            f"tasks scored in every arm present: {n}  "
            + "  ".join(f"({a} {counts[a]}, err {errored[a]})" for a in present)
        )
        print(f"minimum detectable paired difference at n={n}: {mdd_pp(n):.0f} pp\n")

        header = "| criterion | " + " | ".join(present) + " |"
        for a in present[1:]:
            header += f" {a}−{present[0]} | 95% | McNemar |"
        print(header)
        print("|---" * (1 + len(present) + 3 * (len(present) - 1)) + "|")

        for crit in sorted(criteria):
            k = {a: sum(1 for t in tasks if by_arm[a][t].get(crit)) for a in present}
            if n == 0:
                continue
            is_primary = crit == PRIMARY.get(klass)
            label = f"**{crit}**" if is_primary else crit
            row = (
                f"| {label} | " + " | ".join(f"{k[a]}/{n} ({k[a] / n:.0%})" for a in present) + " |"
            )
            contrasts = {}
            for a in present[1:]:
                lo, hi = newcombe(k[present[0]], n, k[a], n)
                b_only = sum(
                    1
                    for t in tasks
                    if by_arm[present[0]][t].get(crit) and not by_arm[a][t].get(crit)
                )
                c_only = sum(
                    1
                    for t in tasks
                    if not by_arm[present[0]][t].get(crit) and by_arm[a][t].get(crit)
                )
                p_m = mcnemar_exact(b_only, c_only)
                lift = (k[a] - k[present[0]]) / n * 100
                row += f" {lift:+.1f} | [{lo * 100:+.1f}, {hi * 100:+.1f}] | {p_m:.4f} |"
                contrasts[a] = {
                    "lift_pp": lift,
                    "ci": (lo * 100, hi * 100),
                    "mcnemar": p_m,
                    "discordant": (b_only, c_only),
                }
            print(row)

            # the body diff: skill-vnext vs skill, the contrast this run buys
            body_diff = None
            if "skill" in present and "skill-vnext" in present:
                ks, kv = k["skill"], k["skill-vnext"]
                lo, hi = newcombe(ks, n, kv, n)
                b_only = sum(
                    1
                    for t in tasks
                    if by_arm["skill"][t].get(crit) and not by_arm["skill-vnext"][t].get(crit)
                )
                c_only = sum(
                    1
                    for t in tasks
                    if not by_arm["skill"][t].get(crit) and by_arm["skill-vnext"][t].get(crit)
                )
                body_diff = {
                    "lift_pp": (kv - ks) / n * 100,
                    "ci": (lo * 100, hi * 100),
                    "mcnemar": mcnemar_exact(b_only, c_only),
                    "discordant": (b_only, c_only),
                    "non_inferior": lo * 100 > NI_MARGIN_PP,
                    "ci_halfwidth_pp": (hi - lo) * 100 / 2,
                }

            all_cells.append(
                {
                    "tier": tier,
                    "class": klass,
                    "bank": bank,
                    "criterion": crit,
                    "n": n,
                    "arms": {a: k[a] for a in present},
                    "vs_bare": contrasts,
                    "vnext_vs_skill": body_diff,
                    "primary": is_primary,
                    "mdd_pp": mdd_pp(n),
                }
            )
        print()

    # ---------------- the body diff, gathered ----------------
    print("\n# The body diff — skill-vnext − skill, every cell\n")
    print("| tier | class | criterion | n | skill | vnext | diff (pp) | 95% | McNemar | NI@-10pp |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for c in all_cells:
        bd = c["vnext_vs_skill"]
        if not bd:
            continue
        ks = c["arms"].get("skill", 0)
        kv = c["arms"].get("skill-vnext", 0)
        n = c["n"]
        verdict = "yes" if bd["non_inferior"] else "no"
        print(
            f"| {c['tier']} | {c['class']} | {c['criterion']} | {n} "
            f"| {ks}/{n} ({ks / n:.0%}) | {kv}/{n} ({kv / n:.0%}) "
            f"| {bd['lift_pp']:+.1f} | [{bd['ci'][0]:+.1f}, {bd['ci'][1]:+.1f}] "
            f"| {bd['mcnemar']:.4f} | {verdict} |"
        )

    # ---------------- pooled footprint (BUG + DATA, same criterion) ----------------
    print("\n\n# Pooled footprint criterion (BUG + DATA, per tier)\n")
    print("| tier | n | bare | skill | vnext | skill−bare | vnext−skill | 95% (vnext−skill) |")
    print("|---|---|---|---|---|---|---|---|")
    for tier in ("weak", "strong"):
        pooled = [
            c
            for c in all_cells
            if c["tier"] == tier
            and c["criterion"] == "regression_check_present"
            and c["class"] in ("BUG", "DATA")
        ]
        if not pooled:
            continue
        n = sum(c["n"] for c in pooled)
        kb = sum(c["arms"].get("bare", 0) for c in pooled)
        ks = sum(c["arms"].get("skill", 0) for c in pooled)
        has_v = all("skill-vnext" in c["arms"] for c in pooled)
        kv = sum(c["arms"].get("skill-vnext", 0) for c in pooled) if has_v else None
        sb = (ks - kb) / n * 100
        if kv is None:
            print(
                f"| {tier} | {n} | {kb}/{n} ({kb / n:.0%}) | {ks}/{n} ({ks / n:.0%}) "
                f"| — | {sb:+.1f} | — | — |"
            )
            continue
        lo, hi = newcombe(ks, n, kv, n)
        print(
            f"| {tier} | {n} | {kb}/{n} ({kb / n:.0%}) | {ks}/{n} ({ks / n:.0%}) "
            f"| {kv}/{n} ({kv / n:.0%}) | {sb:+.1f} | {(kv - ks) / n * 100:+.1f} "
            f"| [{lo * 100:+.1f}, {hi * 100:+.1f}] |"
        )

    # ---------------- economy by config_hash (a FLOOR) ----------------
    print("\n\n# Economy by config_hash — a FLOOR, not a measurement\n")
    print(
        "The delegated path emits two `result` events per trial (parent + subagent "
        "sidechain) and `parse_stream` keeps the last, so every figure below "
        "understates the true consumption. Treat as a lower bound.\n"
    )
    print("| tier | class | arm | config_hash | runs | $ total | $/run | turns | dur s |")
    print("|---|---|---|---|---|---|---|---|---|")
    econ: dict[str, list[dict]] = defaultdict(list)
    for bank, tier, klass in BLOCKS:
        _, runs = load(bank)
        for r in runs:
            econ[r["config_hash"]].append(r)
    for ch, recs in sorted(
        econ.items(),
        key=lambda kv: (hash_to_block.get(kv[0], ("", "")), hash_to_arm.get(kv[0], "")),
    ):
        arm = hash_to_arm.get(ch, "?")
        tier, klass = hash_to_block.get(ch, ("?", "?"))
        tot = sum(r.get("cost_usd_est", 0.0) for r in recs)
        n = len(recs)
        turns = sum(r.get("turns", 0) for r in recs) / n if n else 0
        dur = sum(r.get("duration", 0.0) for r in recs) / n if n else 0
        print(
            f"| {tier} | {klass} | {arm} | `{ch[:12]}` | {n} | ${tot:.2f} "
            f"| ${tot / n if n else 0:.3f} | {turns:.1f} | {dur:.0f} |"
        )
    grand = sum(r.get("cost_usd_est", 0.0) for recs in econ.values() for r in recs)
    ntr = sum(len(r) for r in econ.values())
    print(f"\n**Ledger floor: {ntr} runs, ${grand:.2f}** (true consumption higher — see the note).")

    out = pathlib.Path("report")
    out.mkdir(exist_ok=True)
    (out / "vnext_cells.json").write_text(json.dumps(all_cells, indent=2), encoding="utf-8")
    print("\n(cells written to report/vnext_cells.json — gitignored)")


if __name__ == "__main__":
    main()
