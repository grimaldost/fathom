"""Analyse the verification-lift MAP matrix: per-cell lift over tier x class.

Reads the six committed ledgers, restricts to the two MAP arms (`bare`, `skill`),
and emits per (tier, class, criterion) the two arm rates with Wilson intervals, the
lift with a Newcombe interval for the difference, a two-sided Fisher exact p, and --
because the arms run the *same* tasks -- the exact McNemar p on the discordant pairs,
which is the test the paired design actually licenses. Economy is summed per
`config_hash`, the identity the ledger keys cost on.

Stdlib only (the repo carries no scipy/numpy). Free -- reads the ledger, spawns
nothing.

    uv run python tasks/verif-lift-authoring/analyse_map.py
"""

from __future__ import annotations

import json
import math
import pathlib
from collections import defaultdict

LEDGER = pathlib.Path("ledger")
ARMS = ("bare", "skill")

# (bank, tier, class) -- the six blocks of the MAP.
BLOCKS = [
    ("verif-lift-bug-v1", "weak", "BUG"),
    ("verif-lift-data-v1", "weak", "DATA"),
    ("verif-lift-trunc-v1", "weak", "TRUNC"),
    ("verif-lift-null-v1", "weak", "NULL"),
    ("verif-lift-bug-strong-v1", "strong", "BUG"),
    ("verif-lift-data-strong-v1", "strong", "DATA"),
]

# The criterion each class was authored to move. `scope_respected` is a false-positive
# veto: on the NULL bank a *drop* is the harm, so its lift is read inverted.
PRIMARY = {
    "BUG": "regression_check_present",
    "DATA": "regression_check_present",
    "TRUNC": "defect_past_slice_handled",
    "NULL": "scope_respected",
}


# --------------------------------------------------------------------------
# statistics -- stdlib implementations
# --------------------------------------------------------------------------


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
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


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p for [[a, b], [c, d]] by the sum-of-small-p rule."""
    n = a + b + c + d
    if n == 0:
        return 1.0
    r1, c1, c2 = a + b, a + c, b + d

    def prob(x: int) -> float:
        return math.comb(c1, x) * math.comb(c2, r1 - x) / math.comb(n, r1)

    lo, hi = max(0, r1 - c2), min(r1, c1)
    p_obs = prob(a)
    tol = 1 + 1e-9
    return min(1.0, sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= p_obs * tol))


def mcnemar_exact(b: int, c: int) -> float:
    """Exact McNemar p on discordant counts b (only-arm1) and c (only-arm2)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5**n)
    return min(1.0, 2 * tail)


# --------------------------------------------------------------------------
# ledger loading
# --------------------------------------------------------------------------


def load(bank: str) -> tuple[list[dict], list[dict]]:
    """Return (trial records, run records) for a bank's MAP arms."""
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
    # config_hash -> arm, recovered from trial records (run records carry no arm name).
    hash_to_arm: dict[str, str] = {}
    hash_to_block: dict[str, tuple[str, str]] = {}

    print("# verification-lift MAP — per-cell lift (arms: bare vs skill, n=1)\n")

    all_cells = []
    for bank, tier, klass in BLOCKS:
        trials, runs = load(bank)
        if not trials:
            print(f"## {tier}/{klass} ({bank}) — NO TRIALS IN LEDGER\n")
            continue

        # by_arm[arm][task_id] = {criterion: bool}
        by_arm: dict[str, dict[str, dict]] = defaultdict(dict)
        for t in trials:
            hash_to_arm[t["config_hash"]] = t["scenario"]
            hash_to_block[t["config_hash"]] = (tier, klass)
            if t.get("status") != "completed":
                continue
            by_arm[t["scenario"]][t["task_id"]] = t.get("verifier_results") or {}

        criteria: set[str] = set()
        for arm in ARMS:
            for res in by_arm.get(arm, {}).values():
                criteria.update(res)

        tasks_both = sorted(set(by_arm.get("bare", {})) & set(by_arm.get("skill", {})))
        print(f"## {tier} / {klass}  ({bank})")
        print(
            f"tasks scored in both arms: {len(tasks_both)}  "
            f"(bare {len(by_arm.get('bare', {}))}, skill {len(by_arm.get('skill', {}))})\n"
        )
        print("| criterion | bare | skill | lift (pp) | Newcombe 95% | Fisher p | McNemar p |")
        print("|---|---|---|---|---|---|---|")

        for crit in sorted(criteria):
            kb = sum(1 for t in tasks_both if by_arm["bare"][t].get(crit))
            ks = sum(1 for t in tasks_both if by_arm["skill"][t].get(crit))
            n = len(tasks_both)
            if n == 0:
                continue
            lo, hi = newcombe(kb, n, ks, n)
            # 2x2 for Fisher: rows = arm, cols = pass/fail
            p_f = fisher_exact(kb, n - kb, ks, n - ks)
            b_only = sum(
                1
                for t in tasks_both
                if by_arm["bare"][t].get(crit) and not by_arm["skill"][t].get(crit)
            )
            c_only = sum(
                1
                for t in tasks_both
                if not by_arm["bare"][t].get(crit) and by_arm["skill"][t].get(crit)
            )
            p_m = mcnemar_exact(b_only, c_only)
            lift = (ks - kb) / n * 100
            is_primary = crit == PRIMARY.get(klass)
            label = f"**{crit}**" if is_primary else crit
            print(
                f"| {label} "
                f"| {kb}/{n} ({kb / n:.0%}) | {ks}/{n} ({ks / n:.0%}) "
                f"| {lift:+.1f} | [{lo * 100:+.1f}, {hi * 100:+.1f}] "
                f"| {p_f:.4f} | {p_m:.4f} |"
            )
            all_cells.append(
                {
                    "tier": tier,
                    "class": klass,
                    "criterion": crit,
                    "n": n,
                    "bare": kb,
                    "skill": ks,
                    "lift_pp": lift,
                    "ci": (lo * 100, hi * 100),
                    "fisher": p_f,
                    "mcnemar": p_m,
                    "discordant": (b_only, c_only),
                    "primary": crit == PRIMARY.get(klass),
                }
            )
        print()

    # ---------------- economy by config_hash ----------------
    print("\n# Economy by config_hash\n")
    print("| tier | class | arm | config_hash | trials | $ total | $/trial | turns | dur s |")
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
    print(f"\n**Total: {ntr} runs, ${grand:.2f}**")

    # ---------------- the map ----------------
    print("\n\n# The MAP — primary criterion only\n")
    print("| tier | class | criterion | bare | skill | lift (pp) | Newcombe 95% | McNemar p |")
    print("|---|---|---|---|---|---|---|---|")
    for c in all_cells:
        if not c["primary"]:
            continue
        print(
            f"| {c['tier']} | {c['class']} | {c['criterion']} "
            f"| {c['bare']}/{c['n']} ({c['bare'] / c['n']:.0%}) "
            f"| {c['skill']}/{c['n']} ({c['skill'] / c['n']:.0%}) "
            f"| {c['lift_pp']:+.1f} | [{c['ci'][0]:+.1f}, {c['ci'][1]:+.1f}] "
            f"| {c['mcnemar']:.4f} |"
        )

    out = pathlib.Path("report")
    out.mkdir(exist_ok=True)
    (out / "map_cells.json").write_text(json.dumps(all_cells, indent=2), encoding="utf-8")
    print("\n(cells written to report/map_cells.json — gitignored)")


if __name__ == "__main__":
    main()
