"""Shared, scenario-blind scoring for the routing-decision-v1 verifiers.

Harness-side library: it sits beside the task dirs (never inside any ``fixtures/``)
so ``taskbank.stage_task`` never copies it into a workspace and the grading
result-view never contains it. It carries NO scenario / arm identity — every arm's
``verify.py`` calls the same code with the same task-fixed reference (the expected
brief ids), so using it cannot bias the blind comparison (ADR-0003).

THE TWO CLASSES OF CRITERION, AND WHY THEY ARE SEPARATE.

``HARD`` — well-formedness. An answer exists, it parses, it covers every brief exactly
once, and every tier named is legal. These gate the exit code. They are decidable
offline, today, with no model outcome data.

``chose__<brief>__<tier>`` — the RECORD of what the arm decided. Three booleans per
brief, exactly one true. These are not graded and never gate: they are the channel by
which the emitted routing reaches the ledger, because fathom's per-trial criteria map
is a flat ``{str: bool}`` and the routing is the measurement.

Routing ACCURACY is deliberately absent. Its ground truth is ``cheapest_adequate_tier``
from the ``model-tier-v2`` outcome table, and that bank is authored and unrun — the
column does not exist. A verifier that scored accuracy now would have to invent the
answer key, which is the one thing this whole design exists to avoid. Accuracy is
computed in ``analysis/routing_mechanisms.py`` by joining the recorded ``chose__``
booleans to that column once it lands, so it is derived from evidence at both ends.
"""

from __future__ import annotations

import json
from pathlib import Path

TIERS = ("weak", "mid", "strong")

HARD = ("answer_present", "covers_every_brief", "tiers_are_legal")

ANSWER_FILE = "routing.json"


def read_routes(view: Path) -> dict[str, str] | None:
    """Return the candidate's ``{brief_id: tier}`` map, or None if unreadable.

    Tolerant only of shape trivia a well-behaved answer might still carry (surrounding
    whitespace, a tier written in mixed case). It is NOT tolerant of a missing file, a
    non-object payload, or a missing ``routes`` key — those are the failure the
    ``answer_present`` criterion exists to report.
    """
    path = view / ANSWER_FILE
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    routes = payload.get("routes")
    if not isinstance(routes, dict):
        return None
    out: dict[str, str] = {}
    for key, value in routes.items():
        if not isinstance(key, str) or not isinstance(value, str):
            return None
        out[key.strip()] = value.strip().lower()
    return out


def score(view: Path, brief_ids: list[str]) -> dict[str, bool]:
    """Emit the flat criteria map for one trial.

    Always emits every key — the hard trio and the full ``chose__`` grid — so the
    per-criterion table has the same columns whether the arm answered or not. An arm
    that wrote nothing scores every key false, which is the honest reading: it made no
    decision, rather than a decision that happens to be absent from the table.
    """
    expected = sorted(brief_ids)
    routes = read_routes(view)

    criteria: dict[str, bool] = {
        "answer_present": routes is not None,
        "covers_every_brief": routes is not None and sorted(routes) == expected,
        "tiers_are_legal": routes is not None
        and bool(routes)
        and all(tier in TIERS for tier in routes.values()),
    }

    for brief in expected:
        chosen = (routes or {}).get(brief)
        for tier in TIERS:
            criteria[f"chose__{brief}__{tier}"] = chosen == tier

    return criteria
