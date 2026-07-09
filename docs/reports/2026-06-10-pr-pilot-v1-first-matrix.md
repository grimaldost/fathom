# Run notes — the series-engine bank first matrix (spec §13)

**Date:** 2026-06-10 · **Bank:** the series-engine bank (dataset_version 1; holdout `csvkit` untouched)
**Matrix:** 3 scenarios × 3 dev tasks × 2 repeats = 18 trials · ceiling $36.00

## Run 1 — INVALID (single arms unarmed)

First execution completed 18/18 trials but the `bare` and `single-long-session`
arms spawned with an **empty tool allowlist under default-deny** — the agents
could not read or write the workspace. Result (pipeline 6/6, others 0/6) is
**discarded**; the 24 affected records are archived at
`ledger/archive/pr-pilot-v1.run1-invalid-unarmed-single-arms.jsonl` (append-only:
archived, not deleted). Root cause: spec seam — §5 said tool lists come "from
the scenario," §4's schema never defined the field; survived DoR, pre-mortem,
and 12 blocking reviews because every PR was faithful to its own section.
Fix `32f23ff`: `tools.allowed/disallowed` in the scenario schema (hashed when
set; absent==empty keeps existing hashes stable), CLI wires them into the
runner with a loud warning on unarmed single-session arms, 4 regression tests.

## Run 2 — VALID

Re-ran with armed single arms: planner showed **"planned: 12 trials (6 already
done)"** — the 6 series trials resumed as complete under their unchanged
config_hash (spec §13 resume criterion demonstrated live; run 2 appended to the
surgered ledger without clobbering — criterion 5).

### Scorecard (n=6 per arm; Wilson 95% CI [61.0%, 100.0%] — directional, not final)

| Scenario | Pass rate | Tokens | Turns | Wall-clock | Sessions/trial | Est. USD |
|---|---|---|---|---|---|---|
| bare | 6/6 | 42,498 | 67 | 346 s | 1.0 | (0 — see defect D2) |
| single-long-session | 6/6 | 43,641 | 65 | 377 s | 1.0 | (0 — see defect D2) |
| series | 6/6 | 199,266 | 270 | 1,432 s | 8.0 | 8.07 |

### Verdict (directional)

On tasks of this size, the **series engine pipeline delivered no quality gain over a
bare single session while spending ~4.6× the tokens, ~4× the wall-clock, and 8
sessions per trial.** Arm deltas duly noted: the pipeline carries human
decomposition, per-PR gates, and review/fix subagents — none of which had
anything to add here. This is consistent with keel doctrine §6: below the
blast-radius / coordination threshold, orchestration is pure overhead. The
bank's tasks proved to be *below* that threshold (bare Opus solved each in
~60 s), so this verdict says "don't use the series engine for tasks this small," not
"the series engine is worthless."

### Experiment-design lesson (v2 bank)

Ceiling effect: with bare at 100%, the matrix cannot discriminate quality.
A discriminating bank needs tasks hard enough that the bare arm sometimes
fails (target: bare pass rate well inside (0,1)). the series-engine v2 bank should
scale difficulty up (larger fixtures, cross-module invariants, longer horizon)
until the bare arm drops; only then does the quality axis carry signal and the
threshold question ("where does decomposition start paying?") become testable.

## Defects found by this run

- **D1 (fixed, `32f23ff`):** scenario schema lacked spawn tool lists → unarmed
  single arms. Regression-tested.
- **D2 (open):** `cost_usd_est` is 0.0 for adapter runs — the subscription
  stream's cost field isn't being picked up by the claude-cli adapter parse.
  Tokens/turns/wall-clock are the primary economy currency (C1) so the verdict
  stands, but fix before any cross-arm USD claims.
- **D3 (open, the series engine):** engine wave-loop exits "All done" after a wave with
  planned waves pending (3 logs in `.pr-outputs/`); `--from` mid-wave resume
  doesn't reschedule downstream waves. Workaround `--only`. To the series engine
  feedback.

## §13 done-criteria status

1. Resumable matrix — demonstrated (run 2 planned 12/18, zero re-spawns). ✓
2. Smoke before paid runs — 5/5 incl. engine-boundary non-bypass. ✓
3. Stdlib-runnable core tests — 283 passing. ✓
4. Full paid run + scorecard with verdict, session counts, economy. ✓
5. Ledger committed; second run appended without clobbering. ✓ (this commit)
