"""Blind analysis of Phase 4 against its pre-registration.

docs/design/2026-07-25-phase4-opus-and-successor-prereg.md, applied verbatim.

Phase 4 measured only the NEW cells; its comparators live in earlier ledgers and are
ingested explicitly:
  * 4b needs the debug `bare-sub` and `presc-sub` footprint baselines -> ledger-phase3
  * 4b needs the null-debug `bare-sub` false-positive baseline       -> ledger-phase2
Every borrowed cell is the same arm, bank, tasks and tier as the Phase-4 arm it is
compared against. Errored trials are dropped as missing data.
"""

import glob
import json
import random
from collections import defaultdict

random.seed(20260725)

CRIT = {
    "e1-verif": "regression_check_present",
    "e1-debug": "second_site_fixed",
    "null-verif": "over_scope",
    "null-debug": "over_scope",
}

# (ledger glob, scenario prefix, arms to keep or None for all)
SOURCES = [
    ("ledger-phase4/*.jsonl", "phase4-", None),
    ("ledger-phase3/e1-debug.jsonl", "phase3-", {"bare-sub", "presc-sub"}),
    ("ledger-phase2/null-debug.jsonl", "phase2-", {"bare-sub"}),
]

cells = defaultdict(lambda: defaultdict(list))  # (bank, arm, tier) -> task -> [bool]
dropped = defaultdict(int)

for pattern, prefix, keep in SOURCES:
    for f in glob.glob(pattern):
        for ln in open(f, encoding="utf-8"):
            r = json.loads(ln)
            if r.get("kind") != "trial":
                continue
            scen = r.get("scenario") or ""
            if not scen.startswith(prefix):
                continue
            bank = r["bank"]
            if bank not in CRIT:
                continue
            rest = scen[len(f"{prefix}{bank}-") :]
            tier = rest.rsplit("-", 1)[1]
            arm = rest.rsplit("-", 1)[0]
            if keep is not None and arm not in keep:
                continue
            if r.get("status") != "completed":
                dropped[(bank, arm, tier)] += 1
                continue
            vr = r.get("verifier_results") or {}
            task = r.get("task_id") or "?"
            cells[(bank, arm, tier)][task].append(bool(vr.get(CRIT[bank])))


def rate(cell):
    vals = [v for lst in cell.values() for v in lst]
    return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)


def boot(a, b, iters=2000):
    tasks = sorted(set(a) | set(b))
    if not tasks:
        return (float("nan"), float("nan"))
    d = []
    for _ in range(iters):
        s = [random.choice(tasks) for _ in tasks]
        xa = [v for t in s for v in a.get(t, [])]
        xb = [v for t in s for v in b.get(t, [])]
        if xa and xb:
            d.append(sum(xa) / len(xa) - sum(xb) / len(xb))
    if not d:
        return (float("nan"), float("nan"))
    d.sort()
    return (d[int(0.05 * len(d))], d[int(0.95 * len(d)) - 1])


def show(bank, arms, tiers, label):
    print(f"\n=== {label} ({CRIT[bank]}) ===")
    for tier in tiers:
        parts = []
        for a in arms:
            rt, n = rate(cells[(bank, a, tier)])
            parts.append(f"{a}={rt:.2f}(n{n})" if n else f"{a}=--")
        print(f"  [{tier}]  " + "  ".join(parts))


def lift(bank, arm, base, tier):
    ra, na = rate(cells[(bank, arm, tier)])
    rb, nb = rate(cells[(bank, base, tier)])
    return None if (na == 0 or nb == 0) else ra - rb


# ------------------------------------------------------------------ 4a: opus gate
show("e1-verif", ["bare-sub", "disc-sub"], ["opus"], "4a opus gate — footprint")
show("null-verif", ["bare-sub", "disc-sub"], ["opus"], "4a opus gate — false positive")

print("\n=== 4a VERDICT (foot-lift >= +0.15 AND FP-lift <= +0.15) ===")
fl = lift("e1-verif", "disc-sub", "bare-sub", "opus")
fp = lift("null-verif", "disc-sub", "bare-sub", "opus")
if fl is None:
    print("  no data")
else:
    ci = boot(cells[("e1-verif", "disc-sub", "opus")], cells[("e1-verif", "bare-sub", "opus")])
    v = (
        "CONFIRMED"
        if (fl >= 0.15 and (fp is None or fp <= 0.15))
        else ("REFUTED" if fl <= 0.05 else "INCONCLUSIVE")
    )
    fps = f"{fp:+.2f}" if fp is not None else "na"
    print(f"  foot-lift {fl:+.2f} (90%CI {ci[0]:+.2f},{ci[1]:+.2f})   FP-lift {fps}   -> {v}")

# ------------------------------------------------------- 4b: successor hypothesis
show(
    "e1-debug",
    ["bare-sub", "presc-sub", "presc-artifact-sub"],
    ["haiku", "sonnet"],
    "4b successor — footprint",
)
show(
    "null-debug",
    ["bare-sub", "presc-sub", "presc-artifact-sub"],
    ["haiku", "sonnet"],
    "4b successor — false positive (the decisive one)",
)

print("\n=== 4b/H3 VERDICT (artifact-arm FP-lift >= +0.20 on >=1 tier, plain presc <= +0.05) ===")
hits = 0
plain_ok = True
for tier in ("haiku", "sonnet"):
    fa = lift("null-debug", "presc-artifact-sub", "bare-sub", tier)
    fpz = lift("null-debug", "presc-sub", "bare-sub", tier)
    if fa is None:
        continue
    ci = boot(
        cells[("null-debug", "presc-artifact-sub", tier)], cells[("null-debug", "bare-sub", tier)]
    )
    hits += int(fa >= 0.20)
    if fpz is not None and fpz > 0.05:
        plain_ok = False
    fz = f"{fpz:+.2f}" if fpz is not None else "na"
    print(
        f"  [{tier}] artifact-arm FP-lift {fa:+.2f} (90%CI {ci[0]:+.2f},{ci[1]:+.2f})  plain-presc {fz}"
    )
fa_vals = [
    lift("null-debug", "presc-artifact-sub", "bare-sub", t)
    for t in ("haiku", "sonnet")
    if lift("null-debug", "presc-artifact-sub", "bare-sub", t) is not None
]
if hits >= 1 and plain_ok:
    print("  H3 VERDICT: CONFIRMED — over-triggering tracks artifact producibility, not register")
elif fa_vals and all(v <= 0.05 for v in fa_vals):
    print("  H3 VERDICT: REFUTED — neither register nor artifact-producibility explains it;")
    print("              NO authoring rule may be derived from the Phase-2 contrast")
else:
    print("  H3 VERDICT: INCONCLUSIVE")

# --------------------------------------------------------- 4c: opus tier gradient
show("e1-verif", ["bare", "classifier-hint"], ["opus"], "4c opus tier gradient (descriptive)")
cg = lift("e1-verif", "classifier-hint", "bare", "opus")
if cg is not None:
    print(f"  classifier-hint lift on opus: {cg:+.2f}   (haiku +0.15, sonnet +0.26 previously)")

if dropped:
    print("\n=== dropped (errored) ===")
    for k, v in sorted(dropped.items()):
        print(f"  {k}: {v}")
