"""Blind verifier for `rate-convention-compute` (scenario-blind, deterministic).

Ground truth: the platform's glossary states CDI annualizes on BUS/252
((1+daily)^252-1) and cupom cambial uses ACT/360 with linear (simple)
compounding. Frozen arithmetic (re-derived independently at design review):
(1.00045^252 - 1) = 12.005% (tolerance +/-0.1pp); (1.02 - 1) / (180/360)
= 4.00% (tolerance +/-0.02pp). Verifier normalizes decimal (0.12) and
percent (12.0) answer forms.
"""

import json
import sys
from pathlib import Path

_ALL = (
    "answers_valid",
    "cdi_basis_252",
    "cdi_rate_correct",
    "cupom_convention_act360",
    "cupom_rate_correct",
)

_CDI_PCT = 12.005
_CUPOM_PCT = 4.00


def _norm(value):
    return value.strip().lower() if isinstance(value, str) else None


def _as_pct(value, expected):
    """Parse a number and normalize decimal-form answers to percent."""
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = float(value.strip().rstrip("%").replace(",", "."))
        except ValueError:
            return None
    if not isinstance(value, (int, float)):
        return None
    value = float(value)
    # accept 0.12005 for 12.005% (decimal form)
    if abs(value * 100.0 - expected) < abs(value - expected):
        return value * 100.0
    return value


def _criteria(root: str) -> dict[str, bool]:
    results = dict.fromkeys(_ALL, False)
    try:
        data = json.loads((Path(root) / "answers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return results
    if not isinstance(data, dict):
        return results

    basis = _norm(data.get("cdi_convention_basis"))
    cdi_pct = _as_pct(data.get("cdi_annualized_pct"), _CDI_PCT)
    convention = _norm(data.get("cupom_convention"))
    cupom_pct = _as_pct(data.get("cupom_rate_pct"), _CUPOM_PCT)

    results["answers_valid"] = None not in (basis, cdi_pct, convention, cupom_pct)
    if basis:
        results["cdi_basis_252"] = "252" in basis
    if cdi_pct is not None:
        results["cdi_rate_correct"] = abs(cdi_pct - _CDI_PCT) <= 0.1
    if convention:
        compact = convention.replace(" ", "").replace("-", "")
        results["cupom_convention_act360"] = ("act/360" in compact or "act360" in compact) and (
            "linear" in compact or "simple" in compact
        )
    if cupom_pct is not None:
        results["cupom_rate_correct"] = abs(cupom_pct - _CUPOM_PCT) <= 0.02
    return results


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"usage_error": False}))
        return 1
    results = _criteria(sys.argv[1])
    print(json.dumps(results, sort_keys=True))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
