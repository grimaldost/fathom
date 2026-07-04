# ADR-0003 — Scoring is blind and result-only; trajectory and economy join after scoring

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

fathom's verdicts compare scenarios, so any leak of scenario identity into scoring
biases exactly the comparison being made. Verified prior art (Terminal-Bench)
deliberately scores only final environment state and ignores agent
commands/output; the pairwise-judging literature shows position bias is systematic
and strongest when candidates are close in quality — the marginal regime fathom must
detect. Multi-session strategies also make trajectory-aware grading incomparable
across arms (one long transcript vs many short ones).

## Decision

Verifiers receive only the final trial workspace (plus the task's fixture
reference) — no scenario metadata in argv or env. Judges receive outputs labeled
A/B with scenario identity stripped, judged in both orders, win only on
agreement, else tie. Trajectory, telemetry, and economy data join the comparison
**after** scoring, as the diagnostic layer, never inside the grade.

## Alternatives considered

- **Trajectory assertions in the grade** (promptfoo-style `trajectory:*`) —
  legitimate for debugging, but grades trajectories that differ structurally per
  strategy arm, so it cannot compare a 1-session trial with a 5-session trial.
- **Absolute rubric scores per scenario, compared arithmetically** — two noisy
  pointwise scores compare worse than one pairwise verdict, and absolute scores
  drift across judge revisions, forking longitudinal history.

## Consequences

- New invariant: **scoring inputs are scenario-blind** — verifier argv/env and
  judge prompts must contain no scenario identifiers; a review-checklist item.
- Strategy comparison (single vs multi-session) is sound by construction: the
  verifier cannot tell how many sessions produced the workspace.
- Diagnosis of *why* an arm lost happens in the report layer over ledger + run
  records, where scenario identity is fully visible.
