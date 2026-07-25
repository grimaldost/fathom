"""Blind analysis of Phase-2 against the pre-registered gates.

Applies the decision rules from docs/design/2026-07-24-dispatch-phase2-preregistration.md
verbatim. Footprint pooled per (band, arm, tier); over_scope on null = false-positive.
Task-clustered bootstrap 90% CI on the decisive contrasts (resample task_ids with
replacement). Also reports per-model cost from run records.

Usage: uv run --no-project -- python scripts-phase2/analyze_phase2.py [ledger-dir]
(default ledger-phase2)
"""

import glob
import json
import random
import sys
from collections import defaultdict

random.seed(20260724)

LEDGER = sys.argv[1] if len(sys.argv) > 1 else "ledger-phase2"

FOOT = {
    "e1-debug": "second_site_fixed",
    "e1-data": "output_correct_on_subtle_case",
    "e1-verif": "regression_check_present",
    "c-debug": "footprint",
    "c-data": "footprint",
    "c-verif": "footprint",
}
SUB_ARMS = {"bare-sub", "gated-sub", "generic-sub"}
TIERS = ["haiku", "sonnet", "opus"]

# outcomes[(band, arm, tier)][task_id] = list[bool]
outcomes = defaultdict(lambda: defaultdict(list))
excluded = defaultdict(int)
errored = defaultdict(int)
cost_by_model = defaultdict(float)
n_by_model = defaultdict(int)


def parse(scenario, bank):
    rest = scenario[len(f"phase2-{bank}-") :]
    tier = rest.rsplit("-", 1)[1]
    arm = rest.rsplit("-", 1)[0]
    return arm, tier


for f in glob.glob(f"{LEDGER}/*.jsonl"):
    for ln in open(f, encoding="utf-8"):
        r = json.loads(ln)
        kind = r.get("kind")
        if kind == "run":
            m = r.get("model_id") or "?"
            cost_by_model[m] += r.get("cost_usd_est") or 0.0
            n_by_model[m] += 1
            continue
        if kind != "trial":
            continue
        bank = r["bank"]
        scen = r.get("scenario") or ""
        if not scen.startswith("phase2-"):
            continue
        arm, tier = parse(scen, bank)
        # An errored trial (infrastructure: auth / usage limit) never ran the agent;
        # its verifier_results are all-False and would be read as "no footprint".
        # Drop it — this is missing data, not a negative observation.
        if r.get("status") != "completed":
            errored[(bank, arm, tier)] += 1
            continue
        task = r.get("task_id") or "?"
        vr = r.get("verifier_results") or {}
        if bank.startswith("null-"):
            outcomes[("null", arm, tier)][task].append(bool(vr.get("over_scope")))
        elif arm in SUB_ARMS:
            outcomes[("SUB", arm, tier)][task].append(bool(vr.get("regression_check_present")))
        elif bank.startswith("c-"):
            if not vr.get("trigger_reached", True):
                excluded[(bank, arm, tier)] += 1
                continue
            outcomes[("C", arm, tier)][task].append(bool(vr.get(FOOT[bank])))
        else:  # e1-* Band-B prompt arms
            outcomes[("B", arm, tier)][task].append(bool(vr.get(FOOT[bank])))


def rate(cell):
    """cell = {task: [bool,...]}; pooled mean + n."""
    vals = [v for lst in cell.values() for v in lst]
    return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)


def boot_lift(cell_a, cell_b, iters=2000):
    """Task-clustered bootstrap of rate(a)-rate(b). Resample the shared task set."""
    tasks = sorted(set(cell_a) | set(cell_b))
    if not tasks:
        return (float("nan"), float("nan"))
    diffs = []
    for _ in range(iters):
        samp = [random.choice(tasks) for _ in tasks]
        a = [v for t in samp for v in cell_a.get(t, [])]
        b = [v for t in samp for v in cell_b.get(t, [])]
        if a and b:
            diffs.append(sum(a) / len(a) - sum(b) / len(b))
    if not diffs:
        return (float("nan"), float("nan"))
    diffs.sort()
    lo = diffs[int(0.05 * len(diffs))]
    hi = diffs[int(0.95 * len(diffs)) - 1]
    return (lo, hi)


def show_band(band, arms):
    print(f"\n=== band {band}: footprint rate by (arm, tier) ===")
    for tier in TIERS:
        cells = {a: outcomes[(band, a, tier)] for a in arms}
        if not any(cells[a] for a in arms):
            continue
        parts = []
        for a in arms:
            rt, n = rate(cells[a])
            parts.append(f"{a}={rt:.2f}(n{n})" if n else f"{a}=--")
        print(f"  [{tier}]  " + "  ".join(parts))


def lift(band, arm, base, tier):
    ra, na = rate(outcomes[(band, arm, tier)])
    rb, nb = rate(outcomes[(band, base, tier)])
    if na == 0 or nb == 0:
        return None
    return ra - rb


print(f"ledger: {LEDGER}")
show_band("B", ["bare", "gate-4a", "gate-placebo", "oracle", "classifier-hint"])
show_band("SUB", ["bare-sub", "gated-sub", "generic-sub"])
show_band("C", ["bare", "oracle"])
show_band("null", ["bare", "gate-4a", "gate-placebo", "oracle", "classifier-hint"])
show_band("null", ["bare-sub", "gated-sub", "generic-sub"])

print("\n=== A3 (PRIMARY): gate-4a vs bare AND vs placebo, per tier ===")
a3_tiers_pass = 0
a3_tiers_refute = 0
for tier in TIERS:
    lb = lift("B", "gate-4a", "bare", tier)
    lp = lift("B", "gate-4a", "gate-placebo", tier)
    if lb is None:
        continue
    cib = boot_lift(outcomes[("B", "gate-4a", tier)], outcomes[("B", "bare", tier)])
    promote = lb is not None and lp is not None and lb >= 0.15 and lp >= 0.15
    refute = lb <= 0.05
    a3_tiers_pass += int(promote)
    a3_tiers_refute += int(refute)
    lp_s = f"{lp:+.2f}" if lp is not None else "  na"
    print(
        f"  [{tier}] gate-4a-bare={lb:+.2f} (90%CI {cib[0]:+.2f},{cib[1]:+.2f})  "
        f"gate-4a-placebo={lp_s}  -> {'PROMOTE-tier' if promote else ('refute-tier' if refute else 'incon')}"
    )
verdict = (
    "PROMOTE" if a3_tiers_pass >= 2 else ("REFUTE" if a3_tiers_refute >= 2 else "INCONCLUSIVE")
)
print(f"  A3 VERDICT (>=2 tiers): {verdict}")

print("\n=== A1: oracle / classifier-hint lift vs bare, per tier ===")
for tier in TIERS:
    lo = lift("B", "oracle", "bare", tier)
    lc = lift("B", "classifier-hint", "bare", tier)
    if lo is None and lc is None:
        continue
    los = f"{lo:+.2f}" if lo is not None else " na"
    lcs = f"{lc:+.2f}" if lc is not None else " na"
    print(f"  [{tier}] oracle-bare={los}  classifier-hint-bare={lcs}")
braw = {t: rate(outcomes[("B", "bare", t)]) for t in TIERS}
print("  bare footprint by tier:", {t: f"{braw[t][0]:.2f}" for t in TIERS if braw[t][1]})

print("\n=== SUBAGENT: gate arms vs bare-sub, per tier (footprint) ===")
for gate in ("gated-sub", "generic-sub"):
    sub_pass = 0
    for tier in TIERS:
        ls = lift("SUB", gate, "bare-sub", tier)
        if ls is None:
            continue
        ci = boot_lift(outcomes[("SUB", gate, tier)], outcomes[("SUB", "bare-sub", tier)])
        ok = ls >= 0.15
        sub_pass += int(ok)
        print(
            f"  [{tier}] {gate} - bare-sub = {ls:+.2f} (90%CI {ci[0]:+.2f},{ci[1]:+.2f}) -> {'lift' if ok else 'no'}"
        )
    print(f"  {gate} VERDICT (>=2 tiers): {'PROMOTE' if sub_pass >= 2 else 'no'}")

print("\n=== SUBAGENT FALSE-POSITIVE (null banks, over_scope vs bare-sub) ===")
for gate in ("gated-sub", "generic-sub"):
    for tier in TIERS:
        fl = lift("null", gate, "bare-sub", tier)
        if fl is None:
            continue
        flag = "" if fl <= 0.15 else "   <-- EXCEEDS +0.15 (over-triggers)"
        print(f"  [{tier}] {gate}: over_scope-lift {fl:+.2f}{flag}")

print("\n=== FALSE-POSITIVE (null over_scope lift vs bare, per tier) ===")
for tier in TIERS:
    for arm in ["gate-4a", "gate-placebo", "oracle", "classifier-hint"]:
        fl = lift("null", arm, "bare", tier)
        if fl is None:
            continue
        flag = "" if fl <= 0.15 else "  <-- exceeds +0.15"
        print(f"  [{tier}] {arm}: over_scope-lift {fl:+.2f}{flag}")

if excluded:
    print("\n=== excluded (trigger_reached=false) ===")
    for k, v in sorted(excluded.items()):
        print(f"  {k}: {v}")

if errored:
    print("\n=== MISSING DATA (errored trials, dropped: agent never ran) ===")
    per_bank = defaultdict(int)
    for (bank, _arm, _tier), v in errored.items():
        per_bank[bank] += v
    for bank in sorted(per_bank):
        print(f"  {bank}: {per_bank[bank]} trials")

print("\n=== cost by model (run records) ===")
tot = 0.0
for m in sorted(cost_by_model):
    print(
        f"  {m:<28} ${cost_by_model[m]:.2f}  (n={n_by_model[m]}, ${cost_by_model[m] / max(n_by_model[m], 1):.4f}/trial)"
    )
    tot += cost_by_model[m]
print(f"  TOTAL ${tot:.2f}")
