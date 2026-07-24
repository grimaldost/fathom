"""Analyze the Stage-1 behavioral screen against the pre-registered gates.

Footprint (present bands) pooled per (band, arm, tier) over the band's tasks;
over_scope (null band) is the false-positive metric. Pre-registered promotion:
footprint-lift vs bare >= +2/6 per tier AND FP-lift vs bare <= +2/6 per tier.
"""

import glob
import json
from collections import defaultdict

FOOT = {
    "e1-debug": "second_site_fixed",
    "e1-data": "output_correct_on_subtle_case",
    "e1-verif": "regression_check_present",
    "c-debug": "footprint",
    "c-data": "footprint",
    "c-verif": "footprint",
}
BAND = {
    "e1-debug": "B",
    "e1-data": "B",
    "e1-verif": "B",
    "c-debug": "C",
    "c-data": "C",
    "c-verif": "C",
    "null-debug": "null",
    "null-data": "null",
    "null-verif": "null",
}

metric = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
excluded = defaultdict(int)

for f in glob.glob("ledger-screen/*.jsonl"):
    for ln in open(f, encoding="utf-8"):
        r = json.loads(ln)
        if r.get("kind") != "trial":
            continue
        bank = r["bank"]
        band = BAND[bank]
        rest = r["scenario"][len(f"screen-{bank}-") :]
        tier = rest.rsplit("-", 1)[1]
        arm = rest.rsplit("-", 1)[0]
        vr = r.get("verifier_results") or {}
        if band == "null":
            metric[band][arm][tier].append(bool(vr.get("over_scope")))
        else:
            if bank.startswith("c-") and not vr.get("trigger_reached", True):
                excluded[(bank, arm, tier)] += 1
                continue
            metric[band][arm][tier].append(bool(vr.get(FOOT[bank])))


def rate(lst):
    return f"{sum(lst)}/{len(lst)}" if lst else "  - "


LANE = {
    "static-registry": "B",
    "classifier-hint": "B",
    "framing-4d": "B",
    "gate-4a": "B",
    "gate-placebo": "B",
    "detector-nudge": "C",
    "retrospective-gate": "C",
}

for band, title in [
    ("B", "FOOTPRINT B-present (e1-*, Lane 2)"),
    ("C", "FOOTPRINT C-present (c-*, Lane 3)"),
    ("null", "OVER_SCOPE null (false-positive)"),
]:
    print(f"\n=== {title} ===")
    for tier in ["haiku", "sonnet"]:
        bare = metric[band]["bare"][tier]
        if not bare:
            continue
        bare_c = sum(bare)
        print(f"  [{tier}]  bare = {rate(bare)}")
        for arm in sorted(metric[band]):
            if arm == "bare":
                continue
            lst = metric[band][arm][tier]
            if not lst:
                continue
            lift = sum(lst) - bare_c
            print(f"      {arm:<20} {rate(lst):>6}   lift {lift:+d}")

print("\n=== PRE-REGISTERED GATE (footprint-lift >= +2 AND FP-lift <= +2, per tier) ===")
for arm, pband in LANE.items():
    for tier in ["haiku", "sonnet"]:
        fp_lst = metric[pband][arm][tier]
        bare_p = metric[pband]["bare"][tier]
        null_lst = metric["null"][arm][tier]
        bare_n = metric["null"]["bare"][tier]
        if not fp_lst or not null_lst:
            continue
        flift = sum(fp_lst) - sum(bare_p)
        fplift = sum(null_lst) - sum(bare_n)
        verdict = "PROMOTE" if (flift >= 2 and fplift <= 2) else "no"
        print(f"  {arm:<20} [{tier}] foot-lift {flift:+d}  FP-lift {fplift:+d}  -> {verdict}")

print("\n=== oracle ceiling (reference) ===")
for band in ["B", "C"]:
    for tier in ["haiku", "sonnet"]:
        o = metric[band]["oracle"][tier]
        b = metric[band]["bare"][tier]
        if o and b:
            print(
                f"  band {band} [{tier}]  bare {rate(b)}  oracle {rate(o)}  lift {sum(o) - sum(b):+d}"
            )

if excluded:
    print("\n=== excluded (trigger_reached=false, invalid) ===")
    for k, v in excluded.items():
        print(f"  {k}: {v}")
