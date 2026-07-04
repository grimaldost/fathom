## Mode
plan -> implement (TDD) -> verify (small patches, test after each)

## Mandatory pre-read
- `docs/specs/2026-06-14-fathom-humble-vs-super-design.md` — §9
- `src/fathom/report.py` — the existing per-criterion pass-rate table and economy table (extend, don't replace)

## Task
Add an efficiency view to the scorecard. Per arm, render: the per-criterion pass rates (already present), mean
tokens (in/out/cache), mean turns, mean wall-clock, a derived quality-per-100k-tokens, and a Pareto-dominance
flag among arms (an arm Pareto-dominates another when it has greater-or-equal quality at less-or-equal tokens).

## Constraints
- The efficiency metric uses TOKENS (not USD) — USD plumbing is PR11's concern and lands separately. Do not
  depend on a cost field here.
- Pure reporting over the existing ledger structure; report regeneration stays idempotent (ADR-0002). Keep the
  existing per-criterion table and the all-truthy pass-rate as-is; add the efficiency view alongside.

## Starting file list
1. `src/fathom/report.py`
2. `tests/test_report.py`

## Definition of done
- [ ] `fathom report humble-vs-super-v1` renders one efficiency row per arm (spec §9 acceptance).
- [ ] Any arm that Pareto-dominates another (>= quality at <= tokens) is flagged — tested with a small synthetic
      ledger fixture covering a dominating and a non-dominating case.
- [ ] All quality gates pass.
