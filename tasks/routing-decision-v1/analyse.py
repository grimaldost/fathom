"""T1 analysis: decision cost, cost audit, and the pre-registered agreement stop rule.

Run from the fathom worktree once the T1 block has landed.

TWO CORRECTIONS OVER THE FIRST DRAFT, both found on chunk-1 data:

1. The modal route is computed per (arm, TASK, brief), never pooled across tasks. The
   same brief appears in `route-1-mechanical` and `route-9-mixed`, and pooling them
   conflated two different presentation contexts — which turned out to change the route
   (see the K=1 vs K=9 section). Pooling also manufactured ties that silently shrank the
   agreement denominator from 9 to 8.
2. Agreement is reported PER DECIDING TIER and never as a single number. On chunk-1 data
   the rubric agreed with unaided judgment 9/9 at the strong tier and 4/9 at the weak
   tier; a pooled figure would have hidden the only interesting thing in the result.
"""

from __future__ import annotations

import json
import statistics as st
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from fathom import routing as r  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "ledger" / "routing-decision-v1.jsonl"
PROV = Path(__file__).resolve().parent / "provenance.toml"
MODEL_OF_TIER = {
    "weak": "claude-haiku-4-5",
    "mid": "claude-sonnet-5",
    "strong": "claude-opus-5",
}
MECHS = ("none", "shortcuts", "rubric")
TIERS = ("weak", "mid", "strong")
K1, K9 = "route-1-mechanical", "route-9-mixed"

# v1 ledger medians for the current lineup — the execution-cost stand-in until the
# substrate bank runs. Labelled everywhere it is used.
EXEC = {"weak": 0.0756, "mid": 0.2254, "strong": 0.3368}


def main() -> None:
    rows = [json.loads(x) for x in LEDGER.read_text(encoding="utf-8").splitlines() if x.strip()]
    trials = [x for x in rows if x.get("kind") == "trial"]
    runs = [x for x in rows if x.get("kind") == "run"]
    done = [t for t in trials if t.get("status") == "completed"]
    ch2arm = {x["config_hash"]: x["scenario"] for x in trials}
    model_of = {ch: MODEL_OF_TIER[a.rsplit("-", 1)[1]] for ch, a in ch2arm.items()}
    prov = tomllib.loads(PROV.read_text(encoding="utf-8"))["briefs"]

    print(f"=== LEDGER === trials={len(trials)} completed={len(done)} runs={len(runs)}")
    bad = [t for t in trials if t.get("status") != "completed"]
    if bad:
        print(f"  NON-COMPLETED: {[(t['scenario'], t['task_id'], t.get('status')) for t in bad]}")
    reps = sorted({t.get("repeat") for t in done})
    print(f"  repeats present: {reps}")

    # ------------------------------------------------------------------ cost audit
    audit = r.audit_ledger_costs(runs, model_of)
    print(
        f"\n=== COST AUDIT (FATH-B57 live check) ===\n"
        f"  recomputed ${audit['recomputed_usd']:.4f}  reported ${audit['reported_usd']:.4f}  "
        f"ratio={audit['ratio']:.4f}"
    )
    print("  ratio~1.0 => CLI priced cache-aware, fallback never fired.")

    # --------------------------------------------------------------- per-cell cost
    cost = defaultdict(list)
    for x in runs:
        arm = ch2arm.get(x["config_hash"])
        if arm:
            cost[(arm, x["task_id"])].append(
                r.cost_from_usage(model_of[x["config_hash"]], x.get("usage") or {})
            )
    total = sum(v for vals in cost.values() for v in vals)
    print(f"\n=== TOTAL SPEND (recomputed) === ${total:.4f}")

    print(
        f"\n=== MEASURED DECISION COST ===\n{'mech':10s} {'tier':7s} {'K=1':>8s} {'K=9':>8s} "
        f"{'fixed':>8s} {'marg':>8s} {'K=1/task':>9s} {'K=9/task':>9s}"
    )
    fitted = {}
    for mech in MECHS:
        for tier in TIERS:
            arm = f"{mech}-{tier}"
            a, b = cost.get((arm, K1)), cost.get((arm, K9))
            if not a or not b:
                continue
            c1, c9 = st.median(a), st.median(b)
            dc = r.DecisionCost.from_two_points(mech, tier, cost_at_1=c1, cost_at_k=c9, k=9)
            fitted[(mech, tier)] = dc
            print(
                f"{mech:10s} {tier:7s} {c1:8.4f} {c9:8.4f} {dc.fixed_usd:8.4f} "
                f"{dc.marginal_usd:8.4f} {dc.per_task(1):9.4f} {dc.per_task(9):9.4f}"
            )

    # -------------------------------------------------- premium + break-even (measured)
    print("\n=== RUBRIC PREMIUM OVER `none`, MEASURED, and the break-even it implies ===")
    print("    (saving per strong->weak correction at the tau=0.70 adequacy bar;")
    print("     p_weak is how often the weak tier actually passes when it IS adequate)")
    print(
        f"{'deciding':>9s} {'K':>2s} {'premium/task':>13s} {'p_w=1.0':>9s} {'p_w=0.8':>9s} "
        f"{'p_w=0.7':>9s}"
    )
    for tier in TIERS:
        if ("rubric", tier) not in fitted or ("none", tier) not in fitted:
            continue
        for k in (1, 9):
            prem = fitted[("rubric", tier)].per_task(k) - fitted[("none", tier)].per_task(k)
            cells = []
            for pw in (1.0, 0.8, 0.7):
                o = r.TaskOutcome(
                    "t",
                    0,
                    {"weak": pw, "mid": 0.95, "strong": 1.0},
                    EXEC,
                    dict.fromkeys(TIERS, 1.0),
                )
                wc = r.expected_task(o, "weak", max_escalations=r.PRIMARY_MAX_ESCALATIONS)
                save = EXEC["strong"] - wc.expected_cost
                cells.append(f"{prem / save:9.1%}" if save > 0 else "     n/a")
            print(f"{tier:>9s} {k:2d} {prem:13.4f} " + " ".join(cells))

    # ------------------------------------------------------- routes (per arm PER TASK)
    routes = defaultdict(lambda: defaultdict(list))
    for t in done:
        for brief, tier in r.routes_from_criteria(t.get("verifier_results") or {}).items():
            routes[(t["scenario"], t["task_id"])][brief].append(tier)

    def modal_for(arm: str, task: str) -> dict[str, str]:
        return {b: m for b, v in routes[(arm, task)].items() if (m := r.modal_route(v))}

    briefs9 = sorted(prov, key=lambda b: prov[b]["rubric_score"])
    print("\n=== MODAL ROUTES on route-9-mixed ===")
    hdr = " ".join(f"{m[:4]}-{t[0]}" for t in TIERS for m in MECHS)
    print(f"{'brief':28s} {'score':>5s} {'pred':>6s} | {hdr}")
    for b in briefs9:
        cells = " ".join(
            f"{modal_for(f'{m}-{t}', K9).get(b, '-'):>6s}" for t in TIERS for m in MECHS
        )
        print(f"{b:28s} {prov[b]['rubric_score']:5d} {prov[b]['predicted_tier']:>6s} | {cells}")

    # -------------------------------------------------------------- THE STOP RULE
    print("\n=== PRE-REGISTERED STOP RULE (rubric vs none, route-9-mixed, >=8/9 => STOP) ===")
    print("    Reported per deciding tier. A single pooled number would hide the effect.")
    for tier in TIERS:
        a = modal_for(f"rubric-{tier}", K9)
        n = modal_for(f"none-{tier}", K9)
        ag, comp = r.agreement(a, n)
        lo, hi = r.wilson_interval(ag, comp) if comp else (0.0, 1.0)
        verdict = "STOP" if comp and ag >= 8 else "continue"
        print(f"  deciding {tier:6s}: {ag}/{comp}  Wilson [{lo:.2f}, {hi:.2f}]  -> {verdict}")

    print("\n=== rubric vs shortcuts (secondary) ===")
    for tier in TIERS:
        ag, comp = r.agreement(modal_for(f"rubric-{tier}", K9), modal_for(f"shortcuts-{tier}", K9))
        print(f"  deciding {tier:6s}: {ag}/{comp}")

    # ------------------------------------------------ presentation-context sensitivity
    print("\n=== K=1 vs K=9: does PRESENTATION move the route? (fix-clamp2, all arms) ===")
    flips = 0
    for mech in MECHS:
        for tier in TIERS:
            arm = f"{mech}-{tier}"
            a = modal_for(arm, K1).get("fix-clamp2")
            b = modal_for(arm, K9).get("fix-clamp2")
            flag = ""
            if a and b and a != b:
                flips += 1
                flag = "  <- FLIP"
            print(f"  {arm:18s} K=1 {str(a):>6s}   K=9 {str(b):>6s}{flag}")
    print(f"  arms whose route moved with presentation alone: {flips}/9")


if __name__ == "__main__":
    main()
