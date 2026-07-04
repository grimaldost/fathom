# fathom feedback — the series engine recalibration + usefulness/threshold study

- **Date:** 2026-07-01
- **Tool/version:** fathom 0.1.0 (`pyproject.toml`)
- **Context:** used the harness to (a) re-run the `model-tier-v1` calibration with mid = Sonnet 5, and (b) run
  a 2-probe usefulness/threshold study on a NEW bank the series-usefulness bank (task `sheet`, a reactive
  spreadsheet engine, property-graded). Exercised: append-only ledger + content `config_hash` resume, scenario
  authoring, the bank-validation triad, `fathom smoke`, `fathom report`, and the token x price cost fallback.
- **Outcome:** the harness performed excellently — the resume/config_hash model made a 4-arm calibration cost
  one arm, and the free bank-validation gate de-risked new-task authoring before any spend. Two report-view
  gaps surfaced around bumped `dataset_version`.

## What worked
- **Append-only ledger + content-based `config_hash` resume — the star.** The calibration re-run reused **105
  cached cells** (3 June arms x 7 tasks x n=5) for free; only the changed Sonnet 5 arm ran (35 trials). The
  dry-run reported "35 planned (105 already done)" and it held exactly. This is the single most valuable fathom
  property this session — it turned a 4-arm matrix into a 1-arm cost and isolated the one changed variable
  perfectly. (Confirms the surgical-recovery win noted in an earlier calibration run at scale.)
- **The deterministic bank-validation triad** (fixture-fails / reference-solution-passes / baseline-green)
  validated a brand-new property-graded bank FREE before any paid run, and caught a real setup bug early
  (Python-3.14 `unittest discover` needing `tests/__init__.py`) without spend.
- **`fathom smoke`** (8/8, credential-only real-spawn, non-bypass, engine-boundary) — a cheap, decisive go/no-go
  before paid runs.
- **token x price cost fallback** — gave non-zero economy under subscription auth (real cost ~$0), enough to
  compare arms on a list-price basis.

## Friction
- **[MED] phase: report generation.** After bumping `dataset_version` 1 -> 2 for the hardened `sheet`,
  `fathom report` grouped dv1 + dv2 trials under the same arm name (`bare-sonnet5`, 10 trials), conflating the
  easy and hardened tasks. I had to compute dv2 stats directly from the ledger. A naive read of the scorecard
  would silently mix two task versions.
- **[MED] phase: report generation.** The `Model-Tier Calibration` section covers only the 3 fixed pin arms
  (haiku/sonnet/opus by `pin_level`); an extra arm (`sonnet5`) was absent from the calibration table, so I had
  to read per-criterion pass rates by hand to place Sonnet 5 on the capacity ladder.
- **[LOW] phase: run/resume.** The `dataset_version` bump is a manual, easy-to-forget step: a changed
  `verify.py`/instruction WITHOUT a bump would silently resume-skip stale trials (I caught it; the dry-run
  "0 already done" confirmed the bump took).
- **[LOW] phase: analysis.** `pin_level` is constant (`strong` for every `model-tier-v1` run record); arm
  identity lives only in the opaque `config_hash`, so grouping requires re-hashing scenario files.

## Vacuous gates
None observed — the bank-validation triad and smoke were both substantive (each did real work and could fail).

## Proposed promotions / changes
1. **[MED]** Scope `fathom report` to a `dataset_version` (or split/label arms by dv) so a bumped bank's
   scorecard cannot conflate old + new task versions under one arm name. Home: `src/fathom/report.py`.
2. **[MED]** Extend the `Model-Tier Calibration` view to include ALL model arms present, not just the three
   fixed pin tiers, so ad-hoc arms (e.g. `sonnet5`) land on the ladder automatically. Home:
   `src/fathom/calibration.py` / `report.py`.
3. **[LOW]** content-identical-scenario resume as supported —
   the INVERSE risk: warn when a task's content-hash (instruction + `verify.py` + fixtures) changes but
   `dataset_version` did NOT, to prevent a silent stale-resume of superseded trials. Home: taskbank / run planner.
4. **[LOW]** Add an arm-name/tier field to ledger run records (arm identity is currently only in `config_hash`;
   `pin_level` is constant) for direct analysis without catalog inversion. Home: ledger `RunRecord`. Echoes the
   the series engine ask to stamp `tier`/`effective_model` on events.

## Cost (economy — subscription auth, real ~$0; figures are token x price list-equivalents)

| run | trials | est USD | note |
|---|---|---|---|
| model-tier calibration (Sonnet 5 arm) | 35 | ~$11.4 | reused 105 cached cells free |
| usefulness probe 1 (reactive engine) | 5 | ~$4.6 | bare Sonnet 5 = 5/5 |
| usefulness probe 2 (hardened: fill + aggregates) | 5 | ~$8.5 | bare Sonnet 5 = 5/5 |
| **total this session** | **45** | **~$24.5** | authoring + all validation gates were free |
