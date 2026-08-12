"""Acceptance verifier for route-9-mixed (harness-side, scenario-blind).

Reads the candidate's routing decision ONLY from ``argv[1]`` (the result-view). Its
task-constant reference — the expected brief ids — comes from this task directory and
is identical for every arm, so reading it leaks no scenario identity (ADR-0003).

WHAT THIS VERIFIER SCORES, AND WHAT IT DELIBERATELY DOES NOT.

It scores **well-formedness** only: an answer exists, it covers every brief exactly
once, and every tier named is legal. Those are the hard criteria.

It does NOT score routing **accuracy**, because the ground truth for accuracy —
`cheapest_adequate_tier`, per task, from the `model-tier-v2` outcome table — does not
exist yet (that bank is authored and unrun). Scoring accuracy against a placeholder
would manufacture a number, so instead the verifier **records the emitted routing** as
a set of `chose__<brief>__<tier>` booleans. Exactly one is true per brief. Those
booleans travel into the ledger, and the composition analysis
(`analysis/routing_mechanisms.py`) reconstructs the routing from them and joins it to
`cheapest_adequate_tier` when that column lands. Accuracy is therefore computed at
analysis time from recorded evidence, never assumed here.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # the bank dir, so `import routingverify` resolves

import routingverify as rv  # noqa: E402

BRIEF_IDS = [
    "debug-cache-staleness",
    "feature-ndjson-merge",
    "fix-clamp2",
    "fix-decimal-round",
    "fix-ledger-replay",
    "fix-tz-window",
    "plan-migration-order",
    "refactor-dedupe-validators",
    "review-locate-defects",
]


def main() -> int:
    view = Path(sys.argv[1])
    criteria = rv.score(view, BRIEF_IDS)
    print(json.dumps(criteria))
    return 0 if all(criteria[k] for k in rv.HARD) else 1


if __name__ == "__main__":
    sys.exit(main())
