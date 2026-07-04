# fathom feedback — first model/effort calibration study

- **Date:** 2026-06-16
- **Tool/version:** fathom 0.1.0
- **Context:** A new eval *type* on fathom — model-tier calibration (arms = `(model, effort)` pairs,
  not plugins/injections). Exercised `fathom smoke`, `fathom run` (`--dry-run`, `--repeats`,
  `--max-budget-usd`, idempotent resume), `fathom report` + the new `src/fathom/calibration.py` views,
  across a 105-trial matrix + a 10-trial effort sub-study.
- **Outcome:** The harness took a brand-new eval axis with **zero new spawn-path code** (`model`/
  `effort` were already hashed scenario fields); the spine worked under real load; a few CLI/report
  gaps surfaced.

## What worked

- **An arm = a `(model, effort)` pair, for free.** Both already in `config_hash`, so the study
  needed no adapter changes — only new scenarios + bank + report views. The PR04 scenario schema
  generalized cleanly beyond its plugin/inject origin.
- **Idempotent resume is again the hero.** The pilot (`--repeats 2`, 42 trials) and the full run
  (`--repeats 5`) were the *same* bank, so the pilot's trials counted toward the full matrix — zero
  re-spawn; the GO-gate cost nothing extra. No TTL stall this run (the tasks are cheap/fast).
- **Ceiling-as-signal.** Unlike the prior null-result ceilings (bare 6/6), a weak model acing a
  high-scored task IS the calibration signal here — the confusion matrix is non-degenerate even with
  6/7 tasks at 100%. The hard-criteria-fraction metric (partial credit over *designated* hard
  criteria) made that legible.
- **Cost came in ~$20 vs an $80-120 estimate** — single-session, no-plugin tasks are 4-6× cheaper
  than the plugin-armed banks the ceiling was set from.

## Friction

- **[HIGH] `fathom smoke` does not expose `--effort`.** The smoke *module* has an `--effort` arg in its
  `__main__`, but the `fathom smoke` CLI subcommand (`src/fathom/cli.py`) doesn't plumb it, so
  `fathom smoke --effort xhigh` errors `unrecognized arguments`. This blocked a clean FM-7
  (xhigh-acceptance) probe; I had to let the effort *run itself* be the probe.
- **[MED] the auto-mode classifier blocked `fathom smoke --no-engine-boundary`,** reading it as
  "disabling a safety control central to the never-bypassPermissions invariant." The flag only skips
  the engine-boundary check *group* — it disables no security control. Rename it (e.g.
  `--skip-engine-check`) or document it so the flag isn't read as weakening isolation.

## Misses

- **[MED] phase: review/gate — extends `2026-06-14-humble-vs-super-run`#1 (efficiency Pareto flag).**
  The original efficiency-view Pareto flag (`src/fathom/report.py`) still flags an arm if it "beats
  *some* other arm" (i.e. "not the worst"), not strict non-domination — still live for non-
  calibration banks. I added a *correct* strict-non-domination frontier in the new `calibration.py`
  (asserted in `tests/test_calibration.py`) but deliberately did not touch the old view to keep the
  committed golden stable. The old flag should be fixed + the golden updated. (The new frontier even
  exposed what the old one hides: sonnet flips dominated→frontier between n=2 and n=5.)
- **[LOW] phase: task authoring — prompt-complexity ≠ model-difficulty limited the bank.** The reused
  tasks scored mid/strong by the rubric but were easy-for-Haiku, so the bank ceilinged below the
  strong tier (only `nonlocal-parse` discriminated). The independent-rater spread gate caught this
  pre-spend (documented in the bank README), but it left the study one discriminating task.

## Vacuous gates

- None new. The §3 graded-ness test (reference passes / naive fails a hard criterion / partial credit
  reaches `verifier_results`) and the §7/§8 synthetic-ledger tests assert specific cells and the
  dominated→frontier flip — non-vacuous. The smoke gate is 8/8 real spawns.

## Proposed promotions / changes

1. **[HIGH]** Wire `--effort` (and ideally `--model`) into the `fathom smoke` CLI subparser so effort
   levels can be acceptance-probed before a paid effort run. Home: `src/fathom/cli.py` smoke subparser.
2. **[MED]** Promote the **hard-criteria quality fraction** (partial credit over designated hard
   criteria) into the core report for all banks — it's the anti-ceiling metric that made this study
   legible, where the all-truthy `_is_pass` blends the signal away. Home: `src/fathom/report.py`
   (reference impl in `calibration.py`).
3. **[MED]** extends `2026-06-14-humble-vs-super-run`#1 — fix the original efficiency-view Pareto flag
   to strict non-domination (`calibration.py::_pareto` is the reference) and update the golden.
4. **[LOW]** Recalibrate the `$2/trial` ceiling per strategy — ~10× conservative for single-session
   no-plugin arms (actual ~$0.08-0.24/trial). Home: `src/fathom/cli.py` `_CEILING_PER_TRIAL_USD`.
5. **[LOW]** A **"weak-model-fails" task screen** for calibration banks: pre-run candidate tasks on
   the weak model and keep only those it fails, to build a discriminating bank without trusting rubric
   scores (the rubric proved a poor difficulty oracle, §Misses).

## Cost

| Stage | Trials | Est. USD |
|---|---|---|
| smoke (×2) | gates | ~$2 |
| full matrix (incl. pilot via resume) | 105 | ~$16 (Haiku $2.95 / Sonnet $4.84 / Opus $8.40) |
| effort sub-study | 10 | ~$1 |
| **total** | | **~$20** (vs $80-120 ceiling) |
