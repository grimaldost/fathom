"""Acceptance verifier for the E2E `capbrief` (harness-side, scenario-blind, deterministic).

Reads ONLY the result-view path in argv[1] and scores `answers.json` against ground truth
established from treasuryutils source at v1.8.0: calendartools dispatches numpy+polars (NOT
polars-only); its ops return pl.Expr not nw.Expr (do NOT compose in compute.expr, ADR-0107
§4); CdiCurve.get_rate DOES accept pl.Expr (map_batches bridge, shipped by v1.6.0 — so at
tu 1.8.0 the CORRECT q3 answer is "yes").

The two `saw_*` criteria are MANIPULATION CHECKS: the verifier scores them as booleans
without knowing the arm; whether true/false is the *expected* value depends on the arm and
is interpreted at analysis time (control: ctx yes / warning no; treatment: ctx yes /
warning no; drift: ctx yes / warning yes). `ctx_seen` false in ANY arm means the mounted
plugin's SessionStart hook did not reach the agent — the trial is invalid for inference.

Criteria:
- answers_valid            answers.json parses and every capability key has a usable value
- q1_not_polars_only       calendartools_polars_only is false
- q2_no_compose            calendartools_composes_in_compute_expr is false
- q3_correct_yes           get_rate answer == "yes" (the true 1.8.0 capability)
- q3_not_confidently_wrong get_rate answer != "no" (didn't assert the stale false-negative)
- ctx_seen                 agent reports treasuryutils guidance was in its session context
- warning_seen             agent reports a staleness warning was in its session context
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "q1_not_polars_only",
    "q2_no_compose",
    "q3_correct_yes",
    "q3_not_confidently_wrong",
    "ctx_seen",
    "warning_seen",
)


def _as_bool(value):
    """Normalize a JSON bool-ish answer; None if unusable."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
    return None


def _as_enum(value):
    """Normalize the yes/no/uncertain answer; None if unusable."""
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("yes", "no", "uncertain"):
            return low
        if low in ("unknown", "unsure", "cannot verify", "unverifiable", "uncertain."):
            return "uncertain"
    return None


def _criteria(root: str) -> dict[str, bool]:
    results = dict.fromkeys(_ALL, False)
    path = Path(root) / "answers.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results
    if not isinstance(data, dict):
        return results

    q1 = _as_bool(data.get("calendartools_polars_only"))
    q2 = _as_bool(data.get("calendartools_composes_in_compute_expr"))
    q3 = _as_enum(data.get("cdicurve_get_rate_accepts_pl_expr"))
    ctx = _as_bool(data.get("saw_treasuryutils_context"))
    warn = _as_bool(data.get("saw_staleness_warning"))

    results["answers_valid"] = q1 is not None and q2 is not None and q3 is not None
    results["q1_not_polars_only"] = q1 is False
    results["q2_no_compose"] = q2 is False
    results["q3_correct_yes"] = q3 == "yes"
    results["q3_not_confidently_wrong"] = q3 is not None and q3 != "no"
    results["ctx_seen"] = ctx is True
    results["warning_seen"] = warn is True
    return results


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    # Exit code keys on the CAPABILITY criteria only; the manipulation checks are
    # arm-dependent and interpreted at analysis time.
    core = ("answers_valid", "q1_not_polars_only", "q2_no_compose", "q3_correct_yes")
    return 0 if all(results[k] for k in core) else 1


if __name__ == "__main__":
    sys.exit(main())
