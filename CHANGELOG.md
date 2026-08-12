# Changelog

All notable changes to fathom. Format: Keep a Changelog; versioning: SemVer.
Started at 0.2.0 — 0.1.0 is the initial public surface, unrecorded by a changelog.

## [Unreleased]

**Draft, and deliberately ahead of the tree.** This section describes what the next cut will
contain once the seven pending evidence branches merge; no version number is bumped here, and the
cut itself is a separate change that follows those merges. Two of those branches carry their own
`[Unreleased]` block; this one is written as their superset, so the merge resolves by keeping it.
Every entry below names the surface it changes, not the analysis that motivated it — the analyses
are indexed in `docs/STATUS.md`.

The theme, one sentence: 0.2.0 made a measurement provable; this cut makes a **bank** provable —
that its criteria can fail, that its published numbers were read against the ledger as committed —
and it writes down, without fixing them, the instrument defects that stopped the wave's matrices
from being bought.

### Added

- **The ledger index** (`tools/ledger_index.py`, `docs/reports/LEDGER-INDEX.md`). The publication
  ratchet proved a verdict existed somewhere; it could not prove the verdict had been read against
  the ledger as committed. A re-validation report was published against a 10-trial snapshot, an
  eleventh trial was appended to the same ledger later in the same wave, and three documents then
  carried three different control-pool sizes with three different p-values — suite green throughout.
  The index renders each committed ledger's sha256 and per-arm completed counts;
  `tests/test_ledger_coverage.py` regenerates and compares byte-for-byte, so any append turns the
  suite red until it is re-stamped and the re-render diff names exactly which arms moved. It does not
  read prose, and says so in its own docstring rather than implying otherwise.
- **Two bank-discrimination checks — the property `fathom validate` cannot assert.** `validate`
  answers "is this bank satisfiable, and does the untouched fixture leave work"; neither catches the
  failure that has cost the most here, a task where a plausible-but-shallow answer scores the same as
  a good one. `tools/check_naive_refs.py` closes it for fix-shaped tasks: a task declares
  `[naive] must_pass` / `must_fail` in `task.toml` and ships the overlay in `<task>/refs/naive/`, the
  overlay is run through the real verifier, and a task whose naive fix satisfies its discriminating
  criterion is re-authored before the bank is run. A task declaring no `[naive]` table is
  `UNVERIFIABLE` — reported, and blocking under `--strict`, because calling an unmeasured property
  green is the vacuous-gate shape the repo keeps finding elsewhere.
  `tools/check_skeleton_refs.py` closes the same gap for authoring/repair tasks via `refs/skeleton/`.
- **Positive controls are declarable and read by their own rule.** A bank may declare one in
  `scores.toml`'s `[control]` table; `calibration.control_separation` reads it with a one-sided
  Fisher exact test (`calibration.fisher_one_sided`) on per-trial pass counts, renders it as its own
  scorecard section, and excludes it from the confusion matrix and the per-band dose-response.
- **Gate commands can name a harness-side path portably.** `${task_dir}` and `${workspace}` are
  substituted into a scenario's `[gate] extra` commands at **run** time
  (`strategies.gated_session.expand_gate_placeholders`), so the hashed scenario keeps the portable
  template and the arm stays reproducible across checkouts. A command carrying no placeholder is
  byte-identical to before, so no committed resume key moves.
- **A dry-run ceiling that prices multi-spawn arms.** The flat per-trial rail assumes one spawn per
  trial, which is false for `series`: it spends one implementation spawn plus up to
  `max_fix_attempts` fix spawns for every PR in the task's decomposition. The planner now reads the
  task's committed series template and prices accordingly, and prints the arithmetic
  (`N PRs x (1 impl + M fix) spawns`) so a ceiling many times the per-trial rail reads as a fact
  rather than a typo.
- **Fixture generation for a shared-tree bank** (`tools/build_kit_fixtures.py`) — one staged tree is
  the source for eight tasks, so a fixture cannot silently diverge between them and
  `profile.json`'s `staged_sha256` protects the right bytes.

### Changed

- **The tier decision statistic is one draw per trial** (**ADR-0009**, superseding **ADR-0007 D3**
  only — the other five decisions in that document stand). `calibration.arm_task_stats` scored a cell
  by pooling a task's `k` hard criteria across trials, counting `k x n` draws. Measured on the
  committed `ledger/model-tier-v1.jsonl`, a task's hard set comes out all-true or all-false on
  **175 of 175** multi-criterion trials, so the extra draws were copies and every interval was about
  `sqrt(k)` too narrow. A trial is now one Bernoulli draw — every hard criterion true — with the
  Wilson interval on `(passing trials, trials)`, exposed as `draws`. **Committed readings are
  unchanged and pinned by a test**; the repeat counts derived from the old intervals are not, which
  is the point of the change.
- `arm_task_stats` also returns `mixed_trials`, rendered on the scorecard, so the correlation the
  estimator assumes is checkable from the ledger rather than asserted — a nonzero count is the signal
  to re-open ADR-0009.
- **The planned ceiling now follows the cap that will actually bind** — `trials x --max-budget-usd`
  (else the adapter's default), rather than a flat $2/trial decoupled from the flag. Raising the cap
  now raises the printed ceiling instead of hiding behind a constant. The flag's help text leads with
  **PER-SPAWN** and states plainly that fathom has no run total. The rail itself is still per-spawn;
  see `docs/backlog.md` FATH-B04.

### Fixed

- **A `series` trial that the engine refused to integrate was scored `ERRORED`, so it left the
  denominator entirely.** A blocking gate still red after the bounded fix loop is the engine's own
  *task* failure and the contract says it is scored — but since FATH-B03 a non-completed trial drops
  its `verifier_results` and carries `valid=false`, and the report counts only `completed`. The bias
  ran in exactly one direction: every trial the engine could not finish vanished, leaving a pass rate
  conditioned on the engine having succeeded. Such a trial is now `COMPLETED` with the result scored,
  matching how the single-spawn gated arms treat a gate still red after `max_fix_attempts`. An exit
  outside the engine's documented taxonomy stays `ERRORED` — no verdict was stated, so none is
  invented.
- `tools/check_naive_refs.py` counted a declared `[naive] control` task as discriminating, so an
  8-task bank with 7 traps printed "8 discriminate" and two documents carried the inflated number.
  Controls report in their own column, and the summary now names what a PASS actually is: a
  self-consistency property between an overlay and a contract written together, with no agent
  behaviour observed.

### Evidence merged in this cut

Seven analyses, most of them **authored and armed but not bought** — recorded that way deliberately,
because an unbought matrix with a validated instrument is a different state from a null result, and
the repo's failure mode has been letting the two read alike:

- `verif-lift-{bug,data,trunc,null}-v1` — 62 tasks, `validate --strict` clean, `verify-arming` on all
  22 arms, and a 274-workspace pass showing every criterion both satisfiable and violable. Unrun.
- `research-fusion-v1` — the MCP-serving mount vendored and proven to arm on live spawns. Unrun.
- `e2-data-semantics` — bank and three arms authored and pinned. Unrun.
- `humble-vs-super-v5` — authored, then **deliberately not bought** on power grounds: 15 of 16
  criterion-slots sit at 100% in every arm including `bare`.
- `ablation-v2` series arm — authored and repaired; stopped on the rail.
- `model-tier-v2` — the tier-separating bank, authored and repaired twice under adversarial review;
  the second repair is ADR-0009 above. Unrun.
- `keel-kit-ablation-v1` — the four-arm ablation with its ledger and a stage-1 read that licenses no
  cut.

### Instrument defects recorded, not fixed

The wave's field defects are written into `docs/backlog.md` rather than repaired here, so the cut
carries an honest account of what the instrument still gets wrong: **FATH-B49** (economy pooled by
arm name across `config_hash`es — extended with the general statement and the keying rule),
**FATH-B51** (the delegated path undercounts economy; the ×3.81 correction is a budgeting unit, not
a publishable multiplier), **FATH-B52** (`verify-arming`'s false negative on MCP-served mounts, whose
only documented remedy is the unsafe one), **FATH-B53** (no native mutual exclusion for paid runs —
three deadlocks in one day), **FATH-B54** (a gate command passed to the shell unvalidated, which made
one 9/10 unattributable), **FATH-B55** (the credential model does not survive a matrix longer than a
token; long matrices must be chunked and resumable) and **FATH-B56** (a relative `[tools] repo`
resolved against the process cwd, so `fathom smoke` reads 7/8 from a worktree).

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
