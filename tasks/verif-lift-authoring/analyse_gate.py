"""Analyse the SubagentStop gate trio — the arms that decide pre-registered Branch G.

`analyse_vnext.py` owns the body contrast (bare / skill / skill-vnext) and is left
untouched here; this script owns the gate contrast and *imports* that module's
statistical instruments rather than restating them, so both analyses read the same
intervals and the same exact test. Restating them was the alternative and it is the
one that lets the two analyses drift apart silently.

Three arms, weak tier only (a strong-tier gate cell buys an untreated treatment arm —
report §5a, delivery 0/15 at strong):

    bare-gate     bare body   + gate plugin mounted
    skill-gate    skill body  + gate plugin mounted
    placebo-gate  skill body  + a content-free gate that blocks once and says nothing

H3 is the placebo contrast, `skill-gate` − `placebo-gate`. Both arms pay the same extra
blocked turn, so a difference between them is the gate's *content*; a tie says that the
lift such a gate shows against an ungated arm is the extra turn and not the mechanism.

**Delivery is checked before any contrast is read.** A `SubagentStop` gate that never
fired delivered no treatment, and a contrast between an untreated arm and its control
measures nothing — the strong tier already failed in exactly this way. Delivery is
counted from the saved streams by the gate's own verbatim marker, so the run must set
`FATHOM_STREAM_DIR`; with no streams the script says so and declines to certify the
contrast rather than assuming the treatment arrived.

Stdlib only. Free — reads the ledger and the saved streams, spawns nothing.

    uv run python tasks/verif-lift-authoring/analyse_gate.py [stream_dir]
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from analyse_vnext import (  # noqa: E402
    LEDGER,
    mcnemar_exact,
    mdd_label,
    newcombe_paired,
    wilson,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BANK = "verif-lift-bug-v1"
TIER, KLASS = "weak", "BUG"
PRIMARY = "regression_check_present"

# Ordered so each contrast below has its control on the left.
GATE_ARMS = ("bare", "bare-gate", "skill", "skill-gate", "placebo-gate")

# The gate's only delivery route is the injected text. Both markers are verbatim
# from scenarios/verif-lift-assets/gate-discipline/gate.py and the harness that
# injects it; either one present in a stream proves the block reached the model.
HOOK_MARKER = "Stop hook feedback:"
GATE_SENTENCE = "are you actually confident this is correct"

# (label, control arm, treatment arm, what a difference would mean)
CONTRASTS = [
    ("H3 (the placebo contrast)", "placebo-gate", "skill-gate", "the gate's content"),
    ("gate on top of the skill body", "skill", "skill-gate", "the gate, given the body"),
    ("gate without the body", "bare", "bare-gate", "the gate alone"),
]


def load_trials(bank: str) -> dict[str, dict[str, dict]]:
    """arm -> task_id -> verifier_results, completed non-holdout trials only."""
    path = LEDGER / f"{bank}.jsonl"
    by_arm: dict[str, dict[str, dict]] = defaultdict(dict)
    if not path.exists():
        return by_arm
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("kind") != "trial" or rec.get("scenario") not in GATE_ARMS:
            continue
        if rec.get("holdout", False) or rec.get("status") != "completed":
            continue
        by_arm[rec["scenario"]][rec["task_id"]] = rec.get("verifier_results") or {}
    return by_arm


def delivery(stream_dir: pathlib.Path) -> dict[str, tuple[int, int]]:
    """arm -> (streams carrying the gate, streams seen). Filename tag is
    `{bank}--{scenario}--{task}--r{repeat}--a{attempt}--{ms}.ndjson`."""
    seen: dict[str, list[bool]] = defaultdict(list)
    if not stream_dir.is_dir():
        return {}
    for f in sorted(stream_dir.glob("*.ndjson")):
        parts = f.name.split("--")
        if len(parts) < 2:
            continue
        arm = parts[1]
        if arm not in GATE_ARMS:
            continue
        body = f.read_text(encoding="utf-8", errors="replace")
        seen[arm].append(HOOK_MARKER in body or GATE_SENTENCE in body)
    return {a: (sum(v), len(v)) for a, v in seen.items()}


def main() -> None:
    stream_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("streams-gate")
    by_arm = load_trials(BANK)
    present = [a for a in GATE_ARMS if by_arm.get(a)]

    print("# The SubagentStop gate trio — Branch G / H3\n")
    print(f"Bank `{BANK}` ({TIER}/{KLASS}); primary criterion `{PRIMARY}`.\n")

    if not any(a.endswith("-gate") for a in present):
        print(
            "**No gate arm has any completed trial in the ledger.** Branch G stays "
            "undischarged for want of a comparison, which is not the same as a tie — "
            "see the report. Nothing below is computed.\n"
        )
        return

    print("## Delivery — did the treatment arrive?\n")
    dlv = delivery(stream_dir)
    if not dlv:
        print(
            f"**No streams found under `{stream_dir}`.** Delivery is therefore "
            "unmeasured, and an unmeasured delivery is not a delivered treatment: "
            "the contrasts below are reported but **not certified**, because a gate "
            "that never fired would produce exactly the same table as a gate that "
            "fired and did nothing.\n"
        )
    else:
        print("| arm | gate seen in stream | rate | 95% Wilson |")
        print("|---|---|---|---|")
        for a in present:
            k, n = dlv.get(a, (0, 0))
            if not n:
                print(f"| {a} | — | no streams | — |")
                continue
            lo, hi = wilson(k, n)
            print(f"| {a} | {k}/{n} | {k / n:.0%} | [{lo:.0%}, {hi:.0%}] |")
        print(
            "\nThe two ungated arms are the negative control: a marker there would mean "
            "the filename tag, not the mount, is what this counts.\n"
        )

    common = set(by_arm[present[0]])
    for a in present[1:]:
        common &= set(by_arm[a])
    tasks = sorted(common)
    n = len(tasks)
    print(f"\n## Contrasts — tasks scored in every arm present: n={n}")
    print(f"({', '.join(f'{a} {len(by_arm[a])}' for a in present)})")
    print(f"minimum detectable paired difference at n={n}: {mdd_label(n)}\n")
    if n == 0:
        print("No task is scored in every arm present; no paired contrast is computable.\n")
        return

    criteria: set[str] = set()
    for a in present:
        for res in by_arm[a].values():
            criteria.update(res)

    print("| contrast | criterion | control | treatment | diff (pp) | 95% paired | McNemar |")
    print("|---|---|---|---|---|---|---|")
    for label, ctrl, treat, _meaning in CONTRASTS:
        if ctrl not in present or treat not in present:
            continue
        for crit in sorted(criteria):
            kc = sum(1 for t in tasks if by_arm[ctrl][t].get(crit))
            kt = sum(1 for t in tasks if by_arm[treat][t].get(crit))
            both = sum(1 for t in tasks if by_arm[ctrl][t].get(crit) and by_arm[treat][t].get(crit))
            b_only = sum(
                1 for t in tasks if by_arm[ctrl][t].get(crit) and not by_arm[treat][t].get(crit)
            )
            c_only = sum(
                1 for t in tasks if not by_arm[ctrl][t].get(crit) and by_arm[treat][t].get(crit)
            )
            lo, hi = newcombe_paired(both, b_only, c_only, n - both - b_only - c_only)
            star = "**" if crit == PRIMARY else ""
            print(
                f"| {label} | {star}{crit}{star} | {kc}/{n} ({kc / n:.0%}) "
                f"| {kt}/{n} ({kt / n:.0%}) | {(kt - kc) / n * 100:+.1f} "
                f"| [{lo * 100:+.1f}, {hi * 100:+.1f}] | {mcnemar_exact(b_only, c_only):.4f} |"
            )

    print(
        "\nBranch G fires only on a *measured* tie between `skill-gate` and "
        "`placebo-gate` on the primary criterion, read together with the delivery "
        "table above. A tie at an n whose minimum detectable difference exceeds the "
        "effect being sought is an underpowered read, and the owner's rule forbids "
        "taking a cut from one.\n"
    )


if __name__ == "__main__":
    main()
