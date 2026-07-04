# Is the series engine useful, and did the orchestration threshold move? — v2 findings

- **Date:** 2026-07-01. Bank: the series-usefulness bank (task `sheet`, a reactive spreadsheet engine).
  Companion to the recalibration report + `2026-07-01-pr-pilot-usefulness-v2-design.md`.
- **Question (operator):** do the prior claims (engine = overhead below a coordination threshold; tier-by-
  difficulty) still hold on the CURRENT lineup, and did new models (Sonnet 5) move the threshold?

## What was run
A difficulty ladder for the `bare-sonnet5` arm (plain Claude, single session, effort=high), property-graded:
- **Probe 1 (dv1):** reactive engine — references, precedence, parens, `SUM`, topological recompute, cycle
  detection, error propagation. 9 criteria incl. a random-DAG property test. n=5.
- **Probe 2 (dv2):** the same, HARDENED — added absolute/relative references, a `fill` (copy) operation with
  relative-reference adjustment (the classic spreadsheet gotcha) and off-grid `#REF` handling, and
  `AVG`/`MIN`/`MAX`/`COUNT` aggregates. 15 criteria. n=5.

Each task's triad was validated free before spend (fixture fails all criteria, baseline green, reference
`solution/` passes all criteria). Clean dv2 numbers read from the ledger (the scorecard groups both dv under
the arm name).

## Result — bare Sonnet 5 aced BOTH

| Probe | Task | Criteria | bare-sonnet5 pass | mean turns | mean wall | mean out-tok | est $/trial |
|---|---|---|---|---|---|---|---|
| 1 (dv1) | reactive engine | 9 (incl property) | **5/5** | 12 | ~2.4 min | ~14k | ~$0.92 |
| 2 (dv2) | + fill/abs-rel + aggregates | 15 (incl property, fill-mixed, off-grid) | **5/5** | 19 | ~4.5 min | ~28k | ~$1.71 |

Sonnet 5 **one-shots** a fill-and-aggregate reactive spreadsheet engine — including the relative/absolute
reference fill gotcha and off-grid `#REF` propagation — under property-based grading, in a single session.

## Interpretation — the threshold moved up

- **The orchestration threshold rose substantially.** A multi-file feature with several interacting
  cross-module invariants (parse ↔ dependency graph ↔ evaluator ↔ fill), which in the Opus era might
  plausibly have wanted decomposition, is now routine single-session work for the *mid* tier. Both probes are
  a ceiling (5/5), so the threshold is **bracketed from below** — it sits ABOVE even this task. (We did not
  pinpoint it; that would need substantially harder/longer tasks until bare fails, a larger investment — and
  a deliberate choice NOT to grind, per the study's decision rule.)
- **Combined with the 2026-06-10 series-engine bank matrix** (engine vs bare on easier multi-file tasks: engine
  spent ~4.6× tokens, 8 sessions/trial, for **+0.00 quality** because bare already passed), the picture is
  consistent: **for self-contained feature work, the series engine's decompose/gate/review machinery is overhead** —
  and Sonnet 5 pushes the boundary where that stops being true even higher.
- **Defect-escape was not observable** here — bare never failed, so there were no escaped defects for the
  gates to catch. Demonstrating the engine's *value* (not just its cost) would require a task where bare
  fails, which we could not reach without a much larger authoring + probe investment.

## What this does and does NOT say about the series engine's usefulness
- **Says:** on self-contained, well-specified feature tasks, the engine is overhead for a much larger class
  of work than the Opus-era intuition assumed. Its tier-routing lever is also low-value (calibration showed
  Sonnet 5 near-Opus; routing collapses to "default mid, escalate rarely").
- **Does NOT say the series engine is useless.** Its remaining value lives in dimensions this harness cannot measure
  cleanly (the confound from ADR-0009): **whole-repo gate value** (catching regressions across a large real
  codebase, not a staged subtree), **very long horizons** (10+ interdependent PRs), **convention/guardrail
  enforcement**, and **unattended, cost-capped, resumable batch autonomy** (the "walk away" value, which is
  about operator attention, not per-task quality — inherently not headless-measurable).

## Recommendations
1. **Sharpen the series engine's "when NOT to use" boundary** (README / `docs/concepts.md`): multi-file *feature*
   work that a single current-tier (Sonnet 5) session one-shots is **below** the threshold — reserve the series engine
   for genuinely large, governed, whole-repo, or unattended-batch work. Ground it in this study + 06-10.
2. **Reaffirm the calibration direction:** mid-default (Sonnet 5), Opus/strong escalation-only, routing
   de-emphasized (already reflected in the shipped mid→Sonnet 5 bump + calibration note).
3. **If a true value-side verdict is wanted later:** invest in a bank hard enough that bare fails (defect-
   escape becomes observable) AND address the whole-repo-gate confound — a larger, separately-budgeted study.

## Cost
Study total ≈ **$13.1 est list-equivalent** (probe 1 ~$4.6 + probe 2 ~$8.5), ≈ **$0 real** (subscription
auth). Well under the $25 probe ceiling. Authoring + the triad validation gate were free. Scorecard:
`report/scorecard-pr-pilot-usefulness-v1.md` (note: mixes dv1+dv2 under the arm name; dv2 numbers above are
read directly from the ledger).

