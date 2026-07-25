"""Blind analysis of Phase-3 against its pre-registered rules.

Pre-registration: craft docs/design/2026-07-25-phase3-gate-generalization-prereg.md
  H1 (generalization) CONFIRMED iff disc-sub lifts footprint >= +0.15 on >=2 of the 4
    (discipline x tier) cells AND its over_scope lift stays <= +0.15 on every measured
    null cell. REFUTED iff lift <= +0.05 on >=3 of 4 cells.
  H2 (register replication) CONFIRMED iff, on BOTH new disciplines, presc-sub
    over_scope lift exceeds disc-sub over_scope lift by >= +0.20. REFUTED iff the gap
    is <= +0.05 on both.
Non-completed trials are dropped as missing data (they never ran the agent).
"""

import glob
import json
import random
import sys
from collections import defaultdict

random.seed(20260725)

LEDGER = sys.argv[1] if len(sys.argv) > 1 else "ledger-phase3"

FOOT = {"e1-debug": "second_site_fixed", "e1-data": "output_correct_on_subtle_case"}
DISCIPLINE = {"e1-debug": "debug", "e1-data": "data", "null-debug": "debug", "null-data": "data"}
ARMS = ["bare-sub", "disc-sub", "presc-sub"]
TIERS = ["haiku", "sonnet"]

# outcomes[(kind, discipline, arm, tier)][task] = [bool]; kind in {"foot","fp"}
outcomes = defaultdict(lambda: defaultdict(list))
errored = defaultdict(int)

# Phase-3 deliberately did NOT re-run bare-sub on null-debug: that baseline was
# already banked in Phase 2 (same arm, same bank, same tasks, same tiers). Ingest
# BOTH ledgers and accept a phase2 `bare-sub` null record as the FP baseline, so the
# H2 rule has the comparator it needs. Everything else must be phase3.
BASELINE_LEDGER = "ledger-phase2"
sources = [(f, "phase3-") for f in glob.glob(f"{LEDGER}/*.jsonl")]
sources += [(f, "phase2-") for f in glob.glob(f"{BASELINE_LEDGER}/null-*.jsonl")]

for f, prefix in sources:
    for ln in open(f, encoding="utf-8"):
        r = json.loads(ln)
        if r.get("kind") != "trial":
            continue
        scen = r.get("scenario") or ""
        if not scen.startswith(prefix):
            continue
        if prefix == "phase2-" and "-bare-sub-" not in scen:
            continue  # only the borrowed baseline arm
        bank = r["bank"]
        if bank not in DISCIPLINE:
            continue  # e.g. phase2's null-verif — not a Phase-3 discipline
        rest = scen[len(f"{prefix}{bank}-") :]
        tier = rest.rsplit("-", 1)[1]
        arm = rest.rsplit("-", 1)[0]
        disc = DISCIPLINE[bank]
        if r.get("status") != "completed":
            errored[(bank, arm, tier)] += 1
            continue
        vr = r.get("verifier_results") or {}
        task = r.get("task_id") or "?"
        if bank.startswith("null-"):
            outcomes[("fp", disc, arm, tier)][task].append(bool(vr.get("over_scope")))
        else:
            outcomes[("foot", disc, arm, tier)][task].append(bool(vr.get(FOOT[bank])))


def rate(cell):
    vals = [v for lst in cell.values() for v in lst]
    return (sum(vals) / len(vals), len(vals)) if vals else (float("nan"), 0)


def boot(cell_a, cell_b, iters=2000):
    tasks = sorted(set(cell_a) | set(cell_b))
    diffs = []
    for _ in range(iters):
        samp = [random.choice(tasks) for _ in tasks] if tasks else []
        a = [v for t in samp for v in cell_a.get(t, [])]
        b = [v for t in samp for v in cell_b.get(t, [])]
        if a and b:
            diffs.append(sum(a) / len(a) - sum(b) / len(b))
    if not diffs:
        return (float("nan"), float("nan"))
    diffs.sort()
    return (diffs[int(0.05 * len(diffs))], diffs[int(0.95 * len(diffs)) - 1])


def lift(kind, disc, arm, tier):
    ra, na = rate(outcomes[(kind, disc, arm, tier)])
    rb, nb = rate(outcomes[(kind, disc, "bare-sub", tier)])
    return None if (na == 0 or nb == 0) else ra - rb


print(f"ledger: {LEDGER}\n")
for kind, label in [
    ("foot", "FOOTPRINT (discipline applied)"),
    ("fp", "OVER_SCOPE (trivial edits)"),
]:
    print(f"=== {label} ===")
    for disc in ("debug", "data"):
        for tier in TIERS:
            cells = {a: outcomes[(kind, disc, a, tier)] for a in ARMS}
            if not any(cells[a] for a in ARMS):
                continue
            parts = []
            for a in ARMS:
                rt, n = rate(cells[a])
                parts.append(f"{a}={rt:.2f}(n{n})" if n else f"{a}=--")
            print(f"  [{disc}/{tier}]  " + "  ".join(parts))
    print()

print("=== H1: disc-sub footprint lift vs bare-sub (>= +0.15 on >=2 of 4 cells) ===")
h1_pass = h1_fail = h1_cells = 0
for disc in ("debug", "data"):
    for tier in TIERS:
        lf = lift("foot", disc, "disc-sub", tier)
        if lf is None:
            continue
        h1_cells += 1
        ci = boot(
            outcomes[("foot", disc, "disc-sub", tier)], outcomes[("foot", disc, "bare-sub", tier)]
        )
        h1_pass += int(lf >= 0.15)
        h1_fail += int(lf <= 0.05)
        print(
            f"  [{disc}/{tier}] disc-sub - bare-sub = {lf:+.2f} (90%CI {ci[0]:+.2f},{ci[1]:+.2f})"
        )
print(f"  cells measured: {h1_cells}/4   >=+0.15: {h1_pass}   <=+0.05: {h1_fail}")
if h1_cells < 4:
    print("  H1 VERDICT: INCOMPLETE (pre-registered rule needs all 4 cells)")
else:
    print(
        f"  H1 VERDICT: {'CONFIRMED' if h1_pass >= 2 else ('REFUTED' if h1_fail >= 3 else 'INCONCLUSIVE')}"
    )

print("\n=== H2: does the register gap replicate? (presc FP - disc FP >= +0.20 on BOTH) ===")
gaps = {}
for disc in ("debug", "data"):
    for tier in TIERS:
        lp = lift("fp", disc, "presc-sub", tier)
        ld = lift("fp", disc, "disc-sub", tier)
        if lp is None or ld is None:
            continue
        gaps[(disc, tier)] = lp - ld
        print(
            f"  [{disc}/{tier}] presc over_scope-lift {lp:+.2f}  disc {ld:+.2f}  gap {lp - ld:+.2f}"
        )
if not gaps:
    print("  H2 VERDICT: NOT MEASURABLE — no null-bank data (the FP arms never ran)")
else:
    by_disc = defaultdict(list)
    for (d, _t), g in gaps.items():
        by_disc[d].append(g)
    if len(by_disc) < 2:
        print(
            f"  H2 VERDICT: INCOMPLETE (only {sorted(by_disc)} measured; rule needs BOTH disciplines)"
        )
    else:
        conf = all(min(v) >= 0.20 for v in by_disc.values())
        ref = all(max(v) <= 0.05 for v in by_disc.values())
        print(f"  H2 VERDICT: {'CONFIRMED' if conf else ('REFUTED' if ref else 'INCONCLUSIVE')}")

if errored:
    print("\n=== MISSING DATA (dropped) ===")
    per = defaultdict(int)
    for (b, _a, _t), v in errored.items():
        per[b] += v
    for b in sorted(per):
        print(f"  {b}: {per[b]} errored")
notrun = []
for disc, banks in (("debug", ("e1-debug", "null-debug")), ("data", ("e1-data", "null-data"))):
    for kind, _b in (("foot", banks[0]), ("fp", banks[1])):
        for arm in ARMS:
            for tier in TIERS:
                if not outcomes[(kind, disc, arm, tier)]:
                    notrun.append(f"{kind}/{disc}/{arm}/{tier}")
if notrun:
    print(f"\n=== CELLS WITH NO DATA ({len(notrun)}) ===")
    print("  " + ", ".join(notrun))
