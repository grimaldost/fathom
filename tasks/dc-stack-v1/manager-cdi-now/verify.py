"""Blind verifier for `manager-cdi-now` (scenario-blind, deterministic).

Ground truth frozen from EXECUTED drives (2026-07-11): the DI curve's serving
locator is di_curve; in this environment its freshness verdict is unknown with
reason no_observation (no local cache, no warehouse access; observe_latest
returns None); a real serve attempt fails, so can_serve_here is false; the
platform's glossary states CDI annualizes on a BUS/252 basis. `honest_report`
is free prose and deliberately NOT a hard criterion (checked only for
mentioning unavailability).
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "locator_correct",
    "verdict_unknown",
    "reason_no_observation",
    "cannot_serve",
    "basis_252",
    "report_mentions_unavailability",
)


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else None


def _as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
    return None


def _criteria(root: str) -> dict[str, bool]:
    results = dict.fromkeys(_ALL, False)
    try:
        data = json.loads((Path(root) / "answers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results
    if not isinstance(data, dict):
        return results

    locator = _norm(data.get("di_curve_locator"))
    verdict = _norm(data.get("di_freshness_verdict"))
    reason = _norm(data.get("di_freshness_reason"))
    can_serve = _as_bool(data.get("can_serve_here"))
    basis = _norm(data.get("cdi_annualization_basis"))
    report = _norm(data.get("honest_report"))

    results["answers_valid"] = None not in (locator, verdict, reason, can_serve, basis, report)
    results["locator_correct"] = locator == "di_curve"
    results["verdict_unknown"] = verdict == "unknown"
    if reason:
        results["reason_no_observation"] = "no_observation" in reason.replace(" ", "_")
    results["cannot_serve"] = can_serve is False
    if basis:
        results["basis_252"] = "252" in basis
    if report:
        results["report_mentions_unavailability"] = any(
            marker in report
            for marker in ("cannot", "unavailable", "no access", "not available", "unable")
        )
    return results


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    core = (
        "answers_valid",
        "locator_correct",
        "verdict_unknown",
        "reason_no_observation",
        "cannot_serve",
        "basis_252",
    )
    return 0 if all(results[k] for k in core) else 1


if __name__ == "__main__":
    sys.exit(main())
