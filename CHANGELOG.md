# Changelog

All notable changes to fathom. Format: Keep a Changelog; versioning: SemVer.
Started at 0.2.0 — 0.1.0 is the initial public surface, unrecorded by a changelog.

## [Unreleased]

Release-ritual guardrails, cut from a review of how the 0.4.0 release was actually performed: two
of the day's commits never reached the changelog, and the plugin manifest shipped a release
behind. Every rule that failed was prose; each entry here is the mechanism that replaces one.

### Added

- **`version-sites`, a fourth reconciliation** (`src/fathom/reconcile.py`): `pyproject.toml`,
  `.claude-plugin/plugin.json` and the newest `## [X.Y.Z]` CHANGELOG heading must state the same
  version. The 0.4.0 cut left the manifest at 0.3.0 — pyproject-vs-manifest is exactly a fact this
  repo derives twice, and it was not in the registry the same release created. Runs in the suite
  and in `fathom reconcile`; red proofs replay the 0.4.0 slip.
- **A changelog-currency gate on every PR** (`tools/changelog_currency.py`, ported from keel's —
  the estate's one mechanical enforcement of "record it or declare why not"): a diff touching
  `src/`, `tools/`, `commands/` or `mcp/` fails CI unless `CHANGELOG.md` moves with it or a commit
  in the range carries a `Changelog: not needed (<reason>)` line.

### Changed

- **CI runs on ubuntu and windows, and checks the lock first.** 0.4.0's LF fix closed eight
  ledger digests disagreeing on Windows — a class an ubuntu-only matrix can only see after merge,
  on an estate developed on a Windows machine. `uv lock --check` runs before sync because no test
  can guard lock staleness: `uv run` re-locks before pytest could read the file.

### Fixed

- **`.claude-plugin/plugin.json` states the released version again.** The 0.4.0 release bumped
  every version site except the manifest, and the plugin runtime re-pulls an installed copy only
  when the manifest's version moves — so installed consumers kept resolving the 0.3.0 tree.

## [0.4.0] - 2026-08-28

The reconciliation release. 0.2.0 made a *measurement* provable; 0.3.0 made a *bank* provable.
This cut makes a **record** provable — that a trial's stored identity matches the configuration
that produced it, that a published number still matches the ledger it was read from, and that a
paid arm was ever committed at all.

It comes out of counting how every defect since 0.2.0 was actually discovered: paid-measurement 6,
sustained-operation 6, **post-hoc-audit 3**, authoring-review 2, calibration-before-trust 1. That
third class shares one property — the run completed and every artifact was internally
self-consistent — so no amount of buying or operating finds it. It is also the class that has
already put wrong numbers into circulation. What finds it is holding two independent derivations of
one fact against each other, and exactly one such check existed.

*Record completed 2026-08-29: the section as cut omitted two of the day's commits and the pilot
below. All three describe content the 0.4.0 tree already contains; they were added the day after,
and the omission is part of what motivated the changelog gate now under [Unreleased].*

### Added

- **`fathom reconcile` — a registry of the facts this repo derives twice** (`src/fathom/reconcile.py`).
  A reconciliation is a named function returning discrepancies, so the fourth check costs a function
  rather than the bespoke tool-plus-test pair the first one cost. Free, spawns nothing, exit **13**
  (`EXIT_UNRECONCILED`) when two derivations disagree **or when an exception has gone stale**. It is
  in the gate list in `CLAUDE.md`.
- **The `config_hash` preimage is recorded forward-only**, as an additive `config_preimage` field on
  trial and run records. `scenario.py` already built the canonical hashable dict and threw it away;
  it is now kept (`canonical_config_json`, which `compute_config_hash` also digests, so the two
  cannot drift). **This is what makes the identity check exact**: `sha256(preimage)` either equals
  the stored `config_hash` or the row is corrupt, with no dependence on the tree, an external repo,
  or the process CWD. Empty on every line written before 0.4.0, so no committed line is rewritten and
  no resume key moves (ADR-0002).
- **Three reconciliations ship.** `ledger-index` (the committed stamp against a fresh render — moved
  here from `tests/test_ledger_coverage.py`, which now delegates, because two implementations of one
  comparison is the drift this module exists to catch); `config-hash-preimage` (exact from 0.4.0 on);
  `scenario-known` (completed trials whose arm has no committed scenario).
- **`--max-run-usd`, a rail on what one invocation may spend.** Halts between trials, exit **14**
  (`EXIT_RUN_BUDGET`). There was previously no way to say "this matrix may not cost more than X": the
  only cap was per-spawn, so an operator passing `30` as a program rail would have *raised* each
  spawn's ceiling 6x and licensed ~$1,440 across 48 trials.
- **`--max-spawn-usd`**, the honest name for the per-spawn cap. `--max-budget-usd` keeps working
  **permanently** — it appears in eleven published reports and inside mounted plugin trees whose
  bytes are hashed into `config_hash`, where an edit would fork a committed ledger's resume key.
- **The void-arm registry gate** (`tests/test_void_arms.py`): a registry of arms whose
  configuration is unattributable, and the suite is red while any file under `docs/` quotes a void
  arm's number without a qualifier on the line. The disclosure it mechanizes was six weeks old and
  had not travelled — an audit of all 37 report files found the void `haiku-gate-sg` figures
  unqualified at five load-bearing points of use, including one **negative product verdict**
  (retire the escalation ladder) whose evidence — a trigger that "fired 0/10" — is precisely what
  an inert probe produces. That verdict is **withdrawn as unevidenced** rather than refuted. No
  number is rewritten and no ledger line is touched; the arm's figures stay visible, labelled void.
  A correction that lives in one file is what already failed here.

### Changed

- **A cap of `0` now reaches the spawn.** `if max_budget_usd:` is false for zero, so "spend nothing
  on this spawn" silently fell back to the adapter's $5 default — `None` already spells "no cap", so
  truthiness gave two spellings for "no cap" and none for "spend nothing". This matches the
  default-deny convention in the same function, where an empty allowlist is passed explicitly for the
  same reason. **Not verified:** whether the real CLI accepts a `0` cap; if it does not, a deliberate
  zero now fails loudly instead of quietly spending five dollars.
- **`--max` and other abbreviations no longer parse.** With `--max-run-usd` and `--max-spawn-usd`
  both present, argparse reports an ambiguous option. No committed runbook used an abbreviation, so
  this is disclosure rather than repair.
- The two spellings of the per-spawn cap have **distinct dests**, and passing both with different
  values is an error. One argparse action cannot tell which the operator used, and
  last-parsed-silently-wins is the same class of quiet money bug the rename exists to remove.

### Not built, and why — the version of this release that was designed and then measured

The obvious `config-hash-preimage` check was to recompute each ledger hash from the scenario TOMLs.
It was probed against the real data before it was written, and **58 of 128 distinct
`(bank, config_hash)` pairs — 45%, covering 31% of completed trials and every trial in 7 of 27 banks
— cannot be reconstructed from the tree.** The cause is not authoring sloppiness: `config_hash`
embeds a plugin `tree_sha` computed by globbing a live filesystem, and 79 of 215 mount entries point
at an external repo under active development. That check would have been red-by-construction on the
past *and* would drift red on correct future runs, behind an exception table churning in both
directions — the vacuous gate this release is about. So it was not built, and the forward-only
preimage was built instead.

Deferred to 0.5.0 with the evidence that would justify each: the **run lock** (it needs a decision on
the heartbeat seam and a lock path outside the committed `ledger/`, and its failure is multi-process
on one seat, which this repo's gate cannot exercise); **`ledger-cost`** (downstream of preimage
coverage, which is 0/2985 rows today); the **staging-failure exit code** (`stage_task` is a
`@contextmanager`, so catching it correctly means restructuring the trial loop for a message on a
path that already exits nonzero, and the incident it cites was cross-invocation); and the
**orphan-process preflight** (Windows-specific, so CI could not exercise it).

### Fixed

- `tests/test_ledger_coverage.py` no longer carries its own copy of the freshness comparison.
- **Ledgers are stamped by their canonical LF bytes, not the checkout's.** `append_record` wrote
  platform newlines (CRLF on Windows, which git normalizes away on check-in, so no diff ever showed
  it) and the index digested the working tree's bytes — together they made the freshness gate fail
  on eight ledgers whose per-arm counts all matched, accusing the operator of an append that had
  not happened. `append_record` now opens with `newline="\n"` and the index digests canonical
  bytes, which equals the digest over the committed blob on every platform. The committed index
  reproduces byte-for-byte: no published number moves, no ledger line is rewritten, and both guards
  are proven non-vacuous — reverting either turns its test red.

### Analyses published in this cut

- **`e2-data-semantics`** (18-trial pilot, 18/18 completed, $5.12) — *the pre-registered pilot,
  stopped by its own saturation gate.* `bare` was required to fail its subtle criterion on at least
  2 of the 5 dev traps and failed on 0 of 5; the registered consequence was a stop, and it was
  executed — the remaining 72 dev trials and the 30-trial holdout were not bought. What the stop
  does not license: "the bank cannot discriminate" as a fact — zero failures in five single trials
  is consistent with a true per-trap bare failure rate up to ~45%, so no cut, retirement or
  reversal follows. Every per-claim verdict stays unproven and `oracle_guard.py` stays unlicensed
  (a pre-registered escalation fires on its registered antecedent or not at all).
  `docs/reports/2026-08-11-data-discipline-vnext-proof.md`.
## [0.3.0] - 2026-08-12

The routing-and-evidence release, cut from a two-day measurement wave. 0.2.0 made a *measurement*
provable — the arm was armed, the bank could discriminate, the trial actually ran. This cut makes a
**bank** provable: that its criteria can fail, that a null from it is a null about the treatment
rather than a bank with no headroom, and that every published number was read against the ledger as
committed. It also writes down, without fixing them, the instrument defects the wave hit in field
use.

Every entry in Added / Changed / Fixed names the surface it changes, not the analysis that motivated
it. The wave's own results are in "Analyses published in this cut" below, and indexed with their
verdicts and limits in `docs/STATUS.md`.

### Added

- **The routing substrate: `calibration` now answers a cost question, not only an accuracy one.**
  `needed_tier(tau)` returns the **cheapest tier that clears an adequacy bar** — the per-task ground
  truth a routing mechanism is scored against — replacing `empirical_right_tier` as the primary. The
  relative statistic asked which tier was statistically indistinguishable from the best and answered
  `indeterminate` on ordinary rungs: over six realistic shapes, by exact enumeration, it read the
  right tier **33% of the time at repeats=5** (63% at 10) and was **not monotone in n**, so buying
  repeats did not reliably help. The absolute bar reads **88% / 96%** at 5 / 10. `empirical_right_tier`
  is kept and still rendered, so no committed reading moves.
- **A failure's MODE is measured, because it is a cost term.** Each trial is classified `pass` /
  `gate_caught` (a hard criterion false and the shipped suite red) / `silent` (hard criterion false,
  suite green). A gate-caught failure buys a repair loop — the tier's spend plus the escalation; a
  silent one buys an escape. `mechanism_costs` prices the retry term off the **gate-caught share
  alone** and reports silent failures as `escape_rate`; the two are never summed, because summing
  them would let a mechanism that fails invisibly look cheaper than one that fails loudly.
- **`mechanism_costs` and `discordance_analysis`** compute `C(m) = execution + retry` per task for the
  task-level routing mechanisms (`points`, `reduced`, the fixed tiers, and the `oracle` floor), and
  compare the two rubric-shaped mechanisms **only on the rungs where they route differently** — in
  labels (an exact one-sided sign test) and in dollars (a paired sign-flip permutation test).
  `decision_cost_usd` is reported as **`null`, never `0`**: what a mechanism costs to *run* is
  measured by running it, so every total is a lower bound and says so.
- **`fathom report` emits `report/routing-substrate-<bank>.json`** for any bank declaring a reduced
  mechanism: one row per task with its score, genre, both mechanisms' routing, per-tier pass rate,
  Wilson interval, failure-mode split and mean USD, and the cheapest adequate tier. It is the
  documented input to a separate mechanism-cost comparison — one producer, one schema, one place the
  numbers come from — and the schema is in the bank README.
- **`build_calibration` warns when one arm name maps to more than one `config_hash`.** Cost is
  aggregated per arm for readability but identity is the hash; two configurations averaged under one
  label is silent-wrong, and it now says so.
- **`fathom run --tasks ID[,ID...]` runs only the named task ids.** This is how a *screen* gets
  bought before a full matrix — one band, or the positive control, at higher repeats. `--limit`
  cannot do it: the plan is scenario-major, so `--limit` cuts whole arms off the end rather than
  narrowing the bank. An unknown id is an error, never a silent empty run. Both bought analyses in
  this cut were screens taken this way.

### Changed

- **The word `quality` no longer names a first-attempt pass rate anywhere.** A cross-implementation
  check found `calibration` reporting 0.55 where a consuming programme reported 0.70 on the same
  fixture; both were right and they were different quantities — first-attempt pass rate at the chosen
  tier, versus the probability the work is ultimately correct after a gate-detected repair. The
  estimand is the post-repair figure, because `C(m)` already charges the retry cost and charging for
  an escalation while crediting none of its benefit penalises a cheap-start mechanism twice.
  `mechanisms[].quality` is now **`first_attempt_pass_rate`**, and the routing-substrate artifact's
  `schema_version` goes **1 → 2** so a consumer pinned to 1 fails on the version rather than reading a
  missing key as absent data. `calibration` computes no post-repair figure: it exports the facts that
  bound it (`first_attempt_pass_rate` ≤ post-repair ≤ `1 - escape_rate`) and the consuming analysis
  picks the repair-success assumption between them.
- **The scorecard's dose-response and Pareto columns are renamed to match**: `mean quality` →
  `mean first-attempt pass`, `Δquality vs prev arm` → `Δ first-attempt vs prev arm`, and the section
  heading `Cost-quality Pareto frontier` → `Cost vs first-attempt pass: Pareto frontier`. **Reports
  dated before this change render the older header**; they are dated snapshots of what the tool
  rendered when they were written and are left untouched, as the ledger-index discipline requires.
  The scorecard itself is regenerated from the ledger, so the rename only affects future renders.
- **`per_tier` cells state `failures` explicitly** rather than leaving it as `trials - passing`. The
  general rule, since these cells cross a programme boundary: *a consumer that has to derive a count
  is a consumer that can derive it differently.*
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

### Analyses published in this cut

Some matrices were bought and some were deliberately not, and the two states are kept apart on
purpose: an unbought matrix with a validated instrument is not a null result, and letting the two
read alike has been this repo's recurring failure. Verdicts and their limits are indexed in
`docs/STATUS.md`; the per-arm completed counts every number here is read against are stamped in
`docs/reports/LEDGER-INDEX.md`.

**Bought.**

- **`routing-decision-v1`** (54 trials, 53 completed, $14.04) — *what a routing decision costs, and
  whether a rubric changes one.* Against unaided judgment the rubric leaves **8 of 9** decisions
  unchanged at the mid deciding tier and **9 of 9** at the strong tier, while costing **$0.075 and
  $0.203 more per decision** at K=1. At the strong tier, one decision at a time, the break-even
  correction rate exceeds 100% — there the rubric cannot pay for itself at any correction rate. It
  does change 4 of 9 decisions at the weak deciding tier, every disagreement an upgrade, and the
  premium spans two orders of magnitude across deciding tiers ($0.0021 at weak/K=9 against $0.2026
  at strong/K=1). A separate finding bounds the question rather than answering it: six of nine arms
  routed the one shared brief differently at K=1 than at K=9, so presentation context moves the
  answer independently of mechanism.
- **`model-tier-v2`** (89 trials, $27.60) — **the tier-separating bank the programme had been
  missing.** Its positive control separates decisively: `haiku` 1/10 against `opus5` 10/10,
  one-sided Fisher **p = 5.95e-05** at the pre-registered `min_repeats = 10`. That is what makes the
  bank's other readings interpretable — a null from it is a null about *routing*, not a bank without
  headroom, which is exactly what `model-tier-v1` could never establish. On the four discordant
  briefs the two mechanisms split 2–2 and are reported unpooled, because one verdict over them would
  average away the structure that is the result.
- **Every failure on that bank was invisible to the shipped test suite — 89 trials, 63 passes, 26
  failures, 0 gate-caught, 26 silent.** This is the cut's most consequential measurement, and it is
  a property of the bank's displaced-cause task shapes rather than of any routing policy. A
  start-cheap-and-escalate mechanism has nothing to fire on: its retry term is structurally zero
  here and its apparent cheapness is bought entirely with escapes, so the marginal value of *any*
  better router is bounded by the fact that nothing notices when it is wrong. Both mechanisms also
  come in **under** the oracle's execution cost, which is not a saving — they under-provisioned into
  a failure and never paid for the tier the task required. Any `C(m)` table that nets that against
  correctly-routed briefs reports a saving that does not exist.
- **`verif-lift-{bug,data,trunc,null}-v1`** — the fourth window bought 90 runs ($11.79 in
  ledger-floor units) after three windows that bought nothing. The shipped
  `verification-before-completion` body lifts the footprint criterion **+50.0 pp** at weak/BUG
  (3/10 → 8/10, paired interval excluding zero) — the programme's first positive result — while the
  vNext body gives most of it back (−40.0 pp) and improves nothing anywhere, so **it does not ship**.
  The `SubagentStop` gate ties its placebo exactly (7/10 vs 7/10) with delivery confirmed at 80–90%:
  the gate is not promoted, and the n=10 interval does not license deleting it either. Carried
  caveat: the shipped body costs −30.0 pp on weak/DATA's subtle-case criterion.
- **`premortem-ablation-v1`** ($20.13) — keel's ~500-word pre-mortem core matches the ~2,300-word
  full body on everything measurable, at 80% of the cost; `bare` fails 11 of 12, so the value is in
  being asked at all. Finding *quality* is unmeasured by construction.
- **`keel-kit-ablation-v1`** — the four-arm ablation, with a stage-1 read that licenses no cut.

**Authored, armed, and deliberately not bought** — a different state from a null, recorded as one:

- `research-fusion-v1` — the MCP-serving mount vendored and proven to arm on live spawns.
- `e2-data-semantics` — bank and three arms authored and pinned.
- `humble-vs-super-v5` — stopped on power grounds: 15 of 16 criterion-slots sit at 100% in every
  arm, `bare` included.
- `ablation-v2` series arm — authored and repaired; stopped on the rail.

**What this cut does not claim.** Decision cost is measured for `routing-decision-v1`'s mechanisms
and for nothing else: every `C(m)` from `model-tier-v2` is a lower bound, which is why
`decision_cost_usd` renders as `null` and never `0`. Whether the rubric routes *better* anywhere is
unmeasured — T1 measured what each mechanism emits and what emitting it costs, never whether the
emitted tier was right. How often the mechanisms disagree on a real workload is unmeasured, because
the four briefs are an enriched discordant set from which no per-session figure can be derived. No
threshold move is licensed, and whether escalation recovers cannot be observed at all on a bank
where no failure is gate-visible.

### Instrument defects recorded, not fixed

The wave's field defects are written into `docs/backlog.md` rather than repaired here, so the cut
carries an honest account of what the instrument still gets wrong — **FATH-B49 through FATH-B57**:
**B49** (economy pooled by arm name across `config_hash`es — extended with the general statement and
the keying rule), **B50** (a scenario whose treatment fails to load is warned about and then dropped,
so the matrix runs without it), **B51** (the delegated path undercounts economy; the ×3.81 correction
is a budgeting unit, not a publishable multiplier), **B52** (`verify-arming`'s false negative on
MCP-served mounts, whose only documented remedy is the unsafe one), **B53** (no native mutual
exclusion for paid runs — three deadlocks in one day), **B54** (a gate command passed to the shell
unvalidated, which made one 9/10 unattributable), **B55** (the credential model does not survive a
matrix longer than a token; long matrices must be chunked and resumable), **B56** (a relative
`[tools] repo` resolved against the process cwd, so `fathom smoke` reads 7/8 from a worktree) and
**B57** (under subscription auth the fallback cost estimate discards every cached token, and because
cached input is dominated by the system prompt it understates whichever arm carries the largest
`[context] inject` — a bias that grows with exactly the quantity such a study manipulates). B57 is
latent rather than active: every committed ledger has zero zero-cost rows, and this wave's
`routing-decision-v1` run cross-validated the independent recomputation in `routing.cost_from_usage`
against the CLI's own cache-aware figure at a ratio of 0.9888 over 54 trials.

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
