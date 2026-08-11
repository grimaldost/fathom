# Changelog

All notable changes to fathom. Format: Keep a Changelog; versioning: SemVer.
Started at 0.2.0 — 0.1.0 is the initial public surface, unrecorded by a changelog.

## [Unreleased]

### Added

- **The ledger index** (`tools/ledger_index.py`, `docs/reports/LEDGER-INDEX.md`) —
  the publication ratchet proved a verdict existed somewhere; it could not prove
  the verdict had been read against the ledger as committed. A re-validation
  report was published against a 10-trial snapshot, an eleventh trial was
  appended to the same ledger later in the same wave, and three documents then
  carried three different control-pool sizes and three different p-values with
  the suite green throughout. The index renders each committed ledger's sha256
  and per-arm completed counts; `tests/test_ledger_coverage.py` compares it
  byte-for-byte, so any append turns the suite red until it is re-stamped and the
  re-render diff names the arms that moved. It does not read prose — stated in
  its docstring rather than implied.

### Fixed

- `tools/check_naive_refs.py` counted a declared `[naive] control` task as
  discriminating, so an 8-task bank with 7 traps printed "8 discriminate" and two
  documents carried the inflated number. Controls report in their own column, and
  the summary now names what a PASS is: a self-consistency property between an
  overlay and a contract written together, with no agent behaviour observed.

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

- `skill-pyeng-v1` re-validated: skill arm 3/3 vs 0/8 pooled controls (two-sided Fisher
  p=0.0061), and the skill arm is also the cheapest. Binding limit K=1 task, stated on
  the scorecard.
- Cross-project gate verdicts recorded in `docs/backlog.md`; skeletons and cost plans
  for the two still-unmeasured gates in
  `docs/specs/2026-08-11-cross-project-gate-banks.md`.
