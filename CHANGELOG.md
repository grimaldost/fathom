# Changelog

All notable changes to fathom. Format: Keep a Changelog; versioning: SemVer.
Started at 0.2.0 — 0.1.0 is the initial public surface, unrecorded by a changelog.

## [Unreleased]

### Changed

- **The tier decision statistic is one draw per trial** (ADR-0009, superseding ADR-0007
  D3). `calibration.arm_task_stats` scored a cell by pooling a task's `k` hard criteria
  across trials, which counts `k × n` draws. Measured on the committed
  `ledger/model-tier-v1.jsonl`, a task's hard set comes out all-true or all-false on
  **175 of 175** multi-criterion trials, so the extra draws were copies and every
  interval was ~`√k` too narrow. A trial is now one Bernoulli draw — every hard
  criterion true — with the Wilson CI on `(passing trials, trials)`, exposed as `draws`.
  Committed readings are unchanged (`model-tier-v1` still 1/7 on-diagonal, pinned by a
  test); the repeat counts derived from the old intervals are not.
- `arm_task_stats` also returns `mixed_trials`, rendered on the scorecard, so the
  correlation the estimator assumes is checkable from the ledger rather than asserted.

### Added

- **Positive controls are declarable and read by their own rule.** A bank may declare
  one in `scores.toml`'s `[control]` table; `calibration.control_separation` reads it
  with a one-sided Fisher exact test (`calibration.fisher_one_sided`) on per-trial pass
  counts, renders it as its own scorecard section, and excludes it from the confusion
  matrix and the per-band dose-response.

## [0.2.0] - 2026-08-11

The instrument-trust release: backlog wave 1 (`docs/backlog.md`), driven by the
2026-08-11 feedback-triage and feature-review pass. The theme is one sentence: a
measurement is only evidence when the harness can prove the arm was armed, the bank can
discriminate, and the trial actually ran.

### Added

- **Arming verification** (FATH-B01, `fathom.arming`, `fathom.armingprobe`,
  `fathom verify-arming`): four verification axes over a packaged stream reader
  (`fathom.streams`); `fathom run` pre-flights every armed arm and refuses with
  `EXIT_UNARMED` instead of letting an unarmed arm score. Reverting to
  "declaration is proof" turns 15 tests red.
- **Bank validation** (FATH-B02, `fathom validate`, `EXIT_BANK_INVALID`): the
  bank-validity rule is a machine check run before spend, not a paragraph. Calibrated
  against every committed bank — two false positives found and fixed before trusting it.
- **Un-run trials are structurally distinguishable** (FATH-B03): a trial that never ran
  drops its criteria dict and carries `valid=false`, so it can never read as a real
  negative.
- **Scorecard qualification** (FATH-B05): per-cell N, per-trial min/med/max, the
  contested-Pareto star `*?`, and an Arm Health table.
- **The publication ratchet** (FATH-B06): all five previously-unreported committed
  ledgers now carry written verdicts, and a test fails on any committed ledger with no
  published analysis.

### Fixed

- **Verifier stdout pollution** (FATH-B14): the verifier imports agent-written code, so
  a `print` in the package polluted stdout and discarded the trial — an arm-correlated
  bias, since chattier arms lose more trials. Recovered for every bank.
- **Arming false positive**: ambient account-level MCP connectors were being charged to
  arms that never declared them; the probe now scopes to the arm's own declaration.

### Analyses published under the fixed instrument

- `skill-pyeng-v1` re-validated: skill arm 3/3 vs 0/7 pooled controls (p=0.0083), and
  the skill arm is also the cheapest. Binding limit K=1 task, stated on the scorecard.
- Cross-project gate verdicts recorded in `docs/backlog.md`; skeletons and cost plans
  for the two still-unmeasured gates in
  `docs/specs/2026-08-11-cross-project-gate-banks.md`.
