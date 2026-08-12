"""Analyse the three-arm vNext contrast: bare vs skill vs skill-vnext.

Extends `analyse_map.py` from two arms to three. The added arm injects the
*shipped* vNext body (craft-collection `evals/arms/verification-vnext/`), so the
`skill-vnext` - `skill` contrast is the body diff alone: same delegation
preamble, same framing line, same model, effort, tools and limits.

Every contrast is computed on tasks scored in ALL arms present, because the arms
run the same tasks and the paired test is the one the design licenses. Emits per
(tier, class, criterion): the arm rates with Wilson intervals, each pairwise lift
with a **paired** difference interval, and the exact McNemar p on the discordant
pairs.

The interval and the test must match. An earlier revision printed the Newcombe
hybrid interval for two INDEPENDENT proportions beside an exact McNemar p on the
same row -- arms that run the same tasks, tested as paired and interval-ed as
unpaired. `newcombe_paired` (Newcombe's correlated-proportions method) is the
matching instrument and is materially narrower whenever the pairing is
estimable; `newcombe` is retained only for the pooled table, where per-task
pairing cannot be reconstructed from cell summaries, and is labelled there.

Non-inferiority is decided against a pre-declared margin (NI_MARGIN_PP), one
sided, on the PAIRED lower bound. Before that bound is read, the cell is checked
for whether the margin is decidable at its n at all: if a perfect tie could not
clear the margin, the cell reports **undecidable** rather than a failure, because
a "no" there describes the design and not the result. At NI_MARGIN_PP = -10 pp a
perfect tie needs n >= 35, which no block in this program's funded grid reaches
-- see the report and the plan's X1 block.

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
# 95% PAIRED lower bound of (skill-vnext - skill) sits above -10 pp -- and
# only when that margin is decidable at the cell's n (see ni_decidable_at).
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
    """Newcombe hybrid score interval for p2 - p1, INDEPENDENT proportions.

    Kept for reference and for the two-sample case. **Do not print this beside a
    McNemar p, and never read its lower bound for the non-inferiority test** --
    the arms here run the same tasks, so this interval ignores the pairing and is
    materially wider than the matching instrument. Use `newcombe_paired`.
    """
    if n1 == 0 or n2 == 0:
        return (0.0, 0.0)
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = wilson(k1, n1)
    l2, u2 = wilson(k2, n2)
    d = p2 - p1
    lo = d - math.sqrt((p2 - l2) ** 2 + (u1 - p1) ** 2)
    hi = d + math.sqrt((u2 - p2) ** 2 + (p1 - l1) ** 2)
    return (max(-1.0, lo), min(1.0, hi))


def phi_paired(a: int, b: int, c: int, d: int) -> float:
    """Phi coefficient of the paired 2x2 table, Newcombe's correlation estimate.

    a = pass in both arms, b = arm1 only, c = arm2 only, d = neither.
    Returns 0.0 when any margin is degenerate -- which is Newcombe's own
    recommendation, and makes the paired interval fall back to the independent
    one exactly when an arm sits at 0% or 100% and no correlation is estimable.
    """
    denom = (a + b) * (c + d) * (a + c) * (b + d)
    if denom <= 0:
        return 0.0
    return (a * d - b * c) / math.sqrt(denom)


def newcombe_paired(a: int, b: int, c: int, d: int) -> tuple[float, float]:
    """Newcombe's correlated-proportions interval (method 10) for p2 - p1.

    The paired counterpart of `newcombe`: the same square-and-add construction
    over the two Wilson intervals, with the cross term the pairing supplies. It
    reduces to `newcombe` exactly when phi = 0, so the difference between the two
    IS the pairing that the McNemar test beside it already uses. On ordinary cells
    with positive correlation it removes roughly a fifth to a third of the width.

    This is the interval the non-inferiority margin is read from.

    **Known degeneracy: at phi = 1 this returns a zero-width interval.** A
    perfectly concordant tie away from the boundary (e.g. a=10, b=c=0, d=10)
    gives phi=1, the cross term cancels the radicand, and the interval collapses
    to a point -- which would pass any non-inferiority margin trivially. Do not
    read a feasibility or non-inferiority verdict off such a cell. `ni_decidable_at`
    deliberately probes the ALL-PASS tie instead, where phi is not estimable, the
    fallback to 0 applies, and the answer does not depend on the instrument.
    """
    n = a + b + c + d
    if n == 0:
        return (0.0, 0.0)
    k1, k2 = a + b, a + c
    p1, p2 = k1 / n, k2 / n
    l1, u1 = wilson(k1, n)
    l2, u2 = wilson(k2, n)
    ph = phi_paired(a, b, c, d)
    d_hat = p2 - p1

    def _root(x: float, y: float) -> float:
        # x, y are non-negative Wilson half-widths; the cross term can only
        # shrink the radius, and a negative radicand means the correlation
        # accounts for all of it.
        return math.sqrt(max(0.0, x * x + y * y - 2 * ph * x * y))

    lo = d_hat - _root(p2 - l2, u1 - p1)
    hi = d_hat + _root(u2 - p2, p1 - l1)
    return (max(-1.0, lo), min(1.0, hi))


def ni_decidable_at(n: int, margin_pp: float = None) -> bool:
    """Could a PERFECT TIE at this n clear the non-inferiority margin?

    If not, the cell cannot pass the test on any data, and reporting it as a
    non-inferiority failure would be reporting the design rather than the result.
    """
    if margin_pp is None:
        margin_pp = NI_MARGIN_PP
    if n <= 0:
        return False
    lo, _ = newcombe_paired(n, 0, 0, 0)
    return lo * 100 > margin_pp


def min_n_for_ni(margin_pp: float = None, cap: int = 4000) -> int | None:
    """Smallest n at which a perfect tie clears the margin. None if never."""
    for n in range(1, cap + 1):
        if ni_decidable_at(n, margin_pp):
            return n
    return None


def mcnemar_exact(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) * (0.5**n)
    return min(1.0, 2 * tail)


def mdd_pp(n: int) -> float | None:
    """Minimum detectable difference: the smallest all-one-way discordant split
    at n that exact McNemar calls at p<0.05, in points of the paired rate.

    Returns **None** when no split at this n reaches p<0.05 -- i.e. the cell is
    genuinely undetectable at any effect size. That case starts at n<=5, where
    even a total flip gives p=0.0625.

    The two cases must stay distinguishable. Returning 100.0 for both conflates
    "detectable, but only by a total flip" with "not detectable at all", and the
    conflation was published once as `n=6 | not detectable at any effect size` --
    which is false: mdd_pp(6) is 100 pp, and the exact power at n=6 against a
    near-total lift is 0.94.
    """
    for d in range(1, n + 1):
        if mcnemar_exact(0, d) < 0.05:
            return d / n * 100
    return None


def mdd_label(n: int) -> str:
    """The honest one-line rendering of `mdd_pp`, for tables and prose."""
    m = mdd_pp(n)
    if m is None:
        return "not detectable at any effect size"
    if m >= 100.0:
        return "100 pp (only a total flip)"
    return f"{m:.0f} pp"


def self_check() -> None:
    """Prove the instrument before it reads a ledger, in `generate.py`'s idiom.

    Each assertion pins a defect that was published once and is not to return.
    """
    # 1. The paired interval reduces to the unpaired one exactly at phi = 0.
    for a, b, c, d in [(10, 0, 0, 0), (6, 0, 0, 0), (9, 0, 1, 0)]:
        n = a + b + c + d
        assert phi_paired(a, b, c, d) == 0.0, (a, b, c, d)
        lp = newcombe_paired(a, b, c, d)
        lu = newcombe(a + b, n, a + c, n)
        assert all(abs(x - y) < 1e-12 for x, y in zip(lp, lu)), (lp, lu)

    # 2. Pairing NARROWS the interval whenever the correlation is positive.
    for a, b, c, d in [(10, 1, 4, 5), (8, 2, 5, 5), (14, 1, 3, 2), (20, 2, 6, 12)]:
        n = a + b + c + d
        assert phi_paired(a, b, c, d) > 0, (a, b, c, d)
        lp, hp = newcombe_paired(a, b, c, d)
        lu, hu = newcombe(a + b, n, a + c, n)
        assert (hp - lp) < (hu - lu), (a, b, c, d, hp - lp, hu - lu)

    # 3. mdd keeps "only a total flip" distinct from "nothing is detectable".
    assert mdd_pp(6) == 100.0, mdd_pp(6)
    assert mdd_pp(5) is None, mdd_pp(5)
    assert "not detectable" in mdd_label(5)
    assert "total flip" in mdd_label(6)

    # 4. The pre-declared margin is infeasible at every n this program funds, and
    #    the feasibility probe sits at the all-pass tie where phi is not
    #    estimable -- so the answer does not depend on the instrument.
    for n in (6, 10, 12, 18, 20, 24):
        assert not ni_decidable_at(n), n
    assert min_n_for_ni() == 35, min_n_for_ni()

    # 5. The known degeneracy is real, and nothing reads a verdict off it.
    assert phi_paired(10, 0, 0, 10) == 1.0
    lo, hi = newcombe_paired(10, 0, 0, 10)
    assert hi - lo == 0.0, (lo, hi)


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
    self_check()

    hash_to_arm: dict[str, str] = {}
    hash_to_block: dict[str, tuple[str, str]] = {}

    print("# verification-lift vNext — three-arm per-cell contrast (n=1)\n")
    print(f"Arms: {', '.join(ARMS)}.  Non-inferiority margin: {NI_MARGIN_PP:+.0f} pp ")
    print(
        "(pre-declared; one-sided on the PAIRED lower bound of skill-vnext − skill "
        "— Newcombe's correlated-proportions method, the instrument that matches "
        "the exact McNemar beside it).\n"
    )
    need = min_n_for_ni()
    print(
        f"**Feasibility of the margin, before any data:** a *perfect tie* clears "
        f"{NI_MARGIN_PP:+.0f} pp only at **n >= {need}**. Every cell below n={need} "
        f"reports the margin as **undecidable**, never as a failure — a cell that "
        f"cannot pass on any data measures the design, not the body.\n"
    )

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
        print(f"minimum detectable paired difference at n={n}: {mdd_label(n)}")
        if not ni_decidable_at(n):
            need = min_n_for_ni()
            print(
                f"**non-inferiority at {NI_MARGIN_PP:+.0f} pp is UNDECIDABLE at n={n}** — "
                f"even a perfect tie gives a lower bound of "
                f"{newcombe_paired(n, 0, 0, 0)[0] * 100:+.1f} pp; it needs n>={need}."
            )
        print()

        header = "| criterion | " + " | ".join(present) + " |"
        for a in present[1:]:
            header += f" {a}−{present[0]} | 95% paired | McNemar |"
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
                both = sum(
                    1 for t in tasks if by_arm[present[0]][t].get(crit) and by_arm[a][t].get(crit)
                )
                lo, hi = newcombe_paired(both, b_only, c_only, n - both - b_only - c_only)
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
                both = sum(
                    1
                    for t in tasks
                    if by_arm["skill"][t].get(crit) and by_arm["skill-vnext"][t].get(crit)
                )
                lo, hi = newcombe_paired(both, b_only, c_only, n - both - b_only - c_only)
                decidable = ni_decidable_at(n)
                body_diff = {
                    "lift_pp": (kv - ks) / n * 100,
                    "ci": (lo * 100, hi * 100),
                    "mcnemar": mcnemar_exact(b_only, c_only),
                    "discordant": (b_only, c_only),
                    # A cell whose n cannot clear the margin even on a perfect tie
                    # is UNDECIDABLE, not non-inferior and not inferior. Scoring it
                    # "no" reports the design, not the result.
                    "ni_decidable": decidable,
                    "non_inferior": (lo * 100 > NI_MARGIN_PP) if decidable else None,
                    "ci_halfwidth_pp": (hi - lo) * 100 / 2,
                    "ni_min_n": min_n_for_ni(),
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
    print(
        "| tier | class | criterion | n | skill | vnext | diff (pp) "
        "| 95% paired | McNemar | NI@-10pp |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|")
    for c in all_cells:
        bd = c["vnext_vs_skill"]
        if not bd:
            continue
        ks = c["arms"].get("skill", 0)
        kv = c["arms"].get("skill-vnext", 0)
        n = c["n"]
        if not bd["ni_decidable"]:
            verdict = f"**undecidable at n={n}** (needs n>={bd['ni_min_n']})"
        else:
            verdict = "yes" if bd["non_inferior"] else "no"
        print(
            f"| {c['tier']} | {c['class']} | {c['criterion']} | {n} "
            f"| {ks}/{n} ({ks / n:.0%}) | {kv}/{n} ({kv / n:.0%}) "
            f"| {bd['lift_pp']:+.1f} | [{bd['ci'][0]:+.1f}, {bd['ci'][1]:+.1f}] "
            f"| {bd['mcnemar']:.4f} | {verdict} |"
        )

    # ---------------- pooled footprint (BUG + DATA, same criterion) ----------------
    print("\n\n# Pooled footprint criterion (BUG + DATA, per tier)\n")
    print(
        "The pooled interval below is the **independent-proportions** Newcombe "
        "interval — the per-task pairing is not reconstructable across pooled "
        "cells — so it is wider than the paired truth. The per-cell tables above "
        "carry the paired intervals.\n"
    )
    print(
        "| tier | n | bare | skill | vnext | skill−bare | vnext−skill | 95% unpaired (vnext−skill) |"
    )
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
        # Pooled across cells the per-task pairing is not reconstructable from the
        # cell summaries, so this one interval stays the INDEPENDENT one and is
        # labelled as such in the header. It is wider than the paired truth.
        lo, hi = newcombe(ks, n, kv, n)
        print(
            f"| {tier} | {n} | {kb}/{n} ({kb / n:.0%}) | {ks}/{n} ({ks / n:.0%}) "
            f"| {kv}/{n} ({kv / n:.0%}) | {sb:+.1f} | {(kv - ks) / n * 100:+.1f} "
            f"| [{lo * 100:+.1f}, {hi * 100:+.1f}] |"
        )

    # ---------------- economy by config_hash (a FLOOR) ----------------
    print("\n\n# Economy by config_hash — a FLOOR, not a measurement\n")
    print(
        "On the delegated path the ledger records the parent's final iteration and omits "
        "the subagent's consumption, so every figure below understates the true cost. "
        "Treat as a lower bound. (The earlier two-`result`-events explanation of the "
        "undercount is refuted — see the report's economy section; the floor stands, its "
        "cause is not yet re-derived.)\n"
    )
    print("| tier | class | arm | config_hash | runs | $ total | $/run | turns | dur s |")
    print("|---|---|---|---|---|---|---|---|---|")
    # Keyed on (bank, config_hash), NOT on config_hash alone. An arm whose
    # injected file is identical across two banks resolves to the SAME
    # config_hash in both -- `bare` is hash 3214c0e6bbbb in verif-lift-bug-v1
    # and in verif-lift-trunc-v1 alike. Grouping on the hash alone merged those
    # two banks' runs into one row and labelled it with whichever bank came last
    # in BLOCKS, so weak/BUG vanished from this table while weak/TRUNC reported
    # 14 runs it had not bought. The per-bank key keeps each cell its own.
    econ: dict[tuple[str, str], list[dict]] = defaultdict(list)
    econ_block: dict[tuple[str, str], tuple[str, str]] = {}
    for bank, tier, klass in BLOCKS:
        _, runs = load(bank)
        for r in runs:
            econ[(bank, r["config_hash"])].append(r)
            econ_block[(bank, r["config_hash"])] = (tier, klass)
    for (bank, ch), recs in sorted(
        econ.items(),
        key=lambda kv: (econ_block.get(kv[0], ("", "")), hash_to_arm.get(kv[0][1], "")),
    ):
        arm = hash_to_arm.get(ch, "?")
        tier, klass = econ_block.get((bank, ch), ("?", "?"))
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
