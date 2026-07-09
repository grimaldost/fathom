# Spec — fathom model-tier calibration: is the complexity→model mapping well-tuned?

- **Date:** 2026-06-16
- **Status:** executed (DoR passed; pre-mortem CERTIFIED round 4 after 6 blocking-class folds) — findings: `docs/reports/2026-06-16-model-tier-calibration.md`; the §6 judge was deferred (verifier-only spine)
- **Audience:** fathom maintainer; the keel pre-mortem reviewer; the executor (built directly, not via the series engine — see Execution note)
- **Output artifact(s):** `tasks/model-tier-v1/`, `scenarios/model-tier/`, `src/fathom/grading/judge.py` (wired), `src/fathom/grading/judge_validation.py`, `src/fathom/report.py` (new views), `docs/adr/0007-model-tier-calibration.md`, `docs/reports/2026-06-16-model-tier-calibration.md`

## Context

Measure, with fathom, whether **the series engine's complexity-score → model-tier mapping is well-tuned**: tasks
scored 0-25 route to Haiku (weak), 26-55 to Sonnet (mid), 56-100 to Opus (strong). The mapping is the
routing policy every series the engine runs depends on, yet its own skill admits it has **no observed-run
calibration** — the thresholds are reasoned, not measured. This study supplies the missing evidence for
*this* operator's task distribution.

The harness already supports the experiment with **zero new spawn-path code**: `model` and `effort` are
first-class scenario fields, each resolved and folded into `config_hash` (`src/fathom/scenario.py`), and
`effort` maps verbatim to the CLI `--effort` flag (`src/fathom/adapters/claude_cli.py`). So an *arm is a
(model, effort) pair* exactly as a prior arm was a plugin mount. This builds on the v1 spine
(`docs/specs/2026-06-10-fathom-v1-design.md`) and the plugin-eval precedent
(`docs/specs/2026-06-14-fathom-humble-vs-super-design.md`). Touches ADR-0002 (append-only ledger), ADR-0003
(blind result-only scoring), ADR-0004 (spawn isolation), ADR-0005 (sealed holdout); adds ADR-0007
(calibration study design).

## Grounding (2026-06-16, confirmed before drafting)

- **`model` and `effort` are independent, hashed scenario fields** — both appear on `ScenarioConfig`/
  `ResolvedScenario` and enter the canonical hashable dict (`src/fathom/scenario.py`), so varying either
  forks the ledger correctly and resume keys stay sound.
- **`--effort` accepts `low|medium|high|xhigh|max`** (confirmed via `claude --help`), applied per session
  to any model; it is the *thinking* knob, orthogonal to the *capacity* (model) knob. **Only `medium`/
  `high` are exercised by existing tests/smoke** — `xhigh`/`max` are unproven on a live spawn, so §5/§9
  probe them before the effort layer is authored (FM-7).
- **The mapping under test is pinned external config.** Source: the series engine's `model-tiers` and
  `pr-prompt-scorer`, in repo `/path/to/pr-pilot-main` (the series engine **0.8.1**,
  HEAD **`1c2748f3004c7c32e67b9379944b92e3777020a6`**). Thresholds recorded inline so a drift cannot
  silently move the target: **weak 0-25 → `claude-haiku-4-5`; mid 26-55 → `claude-sonnet-4-6`; strong
  56-100 → `claude-opus-4-8`**. The SHA is re-verified at build time (FM-5).
- **The judge ships dark with NO production caller** — `judge_pairs` in `src/fathom/grading/judge.py` is
  referenced only by its own unit test; the *only* pairwise consumer in `src/fathom/report.py` aggregates
  exclusively where one side's `config_hash` is the `bare` anchor. This study has **no `bare` arm**, so
  lighting the judge is **net-new plumbing** (all-pairs judging + a non-bare aggregation), not a wiring
  tweak (FM-1, FM-8).
- **The dominant failure mode of this harness is the ceiling**, realized twice (STATUS: the series-engine bank
  bare 6/6; `humble-vs-super-v1` 10/11 criteria at 100%). The control here is **Haiku 4.5**, which is
  genuinely capable — "tasks hard enough that Haiku actually fails the high band" is the make-or-break
  risk and is defended by an independent-rater spread gate (§2) and a quantitative pilot GO predicate
  (§9).
- **Three banks' tasks already exist** to draw difficulty rungs from (`tasks/humble-vs-super-v1/`,
  `tasks/humble-vs-super-v3/`, `tasks/humble-vs-super-v4/`) — bug-fix/feature Python tasks, one genre.

## Goal

Deliver a runnable `model-tier-v1` difficulty-ladder bank and the model/effort scenario set that let
`fathom run`/`report` produce a blind verdict on **whether the complexity→tier mapping is well-tuned**:
a calibration confusion matrix (predicted tier vs empirically-right tier), a per-band dose-response
(quality gain × cost per upgrade), a (model×effort) cost-quality Pareto frontier, and a concrete
recommendation back into the `model-tiers` skill — all pilot-gated for discrimination before the full
spend.

## Execution note

The keel PR↔section manifest is used for planning and as each section's exit gate. The sections are
executed **directly by the operator in-session**, not handed to the series engine — the engine
creates `bypassPermissions` subagents that the harness auto-mode classifier blocks, which would break the
"run autonomously to the end" mandate. This is a deliberate routing choice, not a gap; gate commands below
still hold per section.

## Gate commands

All must pass before any commit (project standard, `CLAUDE.md`):

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`  (stdlib-runnable suite)
- `uv run fathom smoke`  (real-spawn isolation gate)

Run-planning (spawns nothing): `uv run fathom run model-tier-v1 --scenarios-dir scenarios/model-tier --dry-run`.

## Non-goals

- **Non-Claude models / cross-vendor routing.** Only the three Claude tiers the mapping assigns. Fable 5
  (frontier) is excluded — unavailable on this account and author-assigned, not score-routed.
- **Re-deriving the series engine's scoring rubric.** Task complexity scores come from running the pinned
  `pr-prompt-scorer` rubric as-is; this study tests the *threshold→model* half, taking the
  score→complexity half as given.
- **A full (model × effort) factorial.** Effort enters *staged*: the main matrix fixes `effort=high`; an
  effort layer is added only on the bands where the pilot shows effort moves quality (§5/§9).
- **Trigger/skill measurement.** No plugins are mounted; this is a pure model/effort study.
- **A cardinal judge quality score.** The pairwise judge yields an ordinal win/tie/loss; it is NOT the
  axis on which ε or the confusion matrix is computed (that is the verifier fraction, §1) — the judge is
  corroboration only (FM-6).
- **Network/execution grading inside the spawn.** Tasks are stdlib-only Python; verifiers run locally,
  offline (fathom constraint C3).

## Invariants touched

- **Blindness** (ADR-0003) — the verifier reads only the result-view; the newly-lit judge sees two
  outputs labeled A/B with model identity removed and order swapped; economy joins after scoring.
- **Append-only ledger** (ADR-0002) — `model`/`effort` already enter `config_hash`; the new bank and arms
  produce new resume keys without rewriting any existing line; judge `GradingRecord`s are appended.
- **Spawn isolation** (ADR-0004) — `--model`/`--effort` are CLI flags on the same isolated, credential-
  only, default-deny spawn; no `bypassPermissions`.
- **Sealed holdout** (ADR-0005) — the bank seals ≥1 task, excluded from `fathom run`, spent only after the
  primary verdict is locked.
- **Stdlib core** — new modules under `src/fathom/` stay stdlib-only.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| Blindness — verifier result-only | enforced | `src/fathom/grading/verifier.py`; result-view handed to grading |
| Blindness — judge A/B identity-stripped + swap-order | planned | §6 wires it and adds the validation harness before any verdict trusts it |
| Append-only ledger | enforced | `src/fathom/ledger.py`; resume key `(bank, dataset_version, task_id, config_hash, repeat)` |
| `config_hash` includes model + effort | enforced | `src/fathom/scenario.py` — both fields in the canonical hashable dict |
| Spawn isolation (default-deny, credential-only config) | enforced | `src/fathom/adapters/claude_cli.py`; `fathom smoke` |
| Sealed holdout excluded from `fathom run` | enforced | `src/fathom/cli.py` non-holdout filter; bank `holdout` list |
| Quality = verifier fraction (partial credit survives) | planned | §3 verify.py exits 0 on valid JSON; §7 report computes the fraction |
| Stdlib-only core modules | review-only | code review; no third-party import under `src/fathom/` |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| Calibration study design + "right tier" operationalization + alternatives | `docs/adr/0007-model-tier-calibration.md` (to be created, §1) |
| Difficulty-ladder bank + per-task rubric scores / predicted tiers / independent re-rating | `tasks/model-tier-v1/` (to be created, §2) |
| Graded multi-criterion (anti-ceiling) verifiers; ≥2 designated HARD criteria | `tasks/model-tier-v1/` (to be created, §3) |
| Model-arm scenarios (Haiku/Sonnet/Opus @ effort=high) | `scenarios/model-tier/` (to be created, §4) |
| Staged effort-layer scenarios + live xhigh/max probe | `scenarios/model-tier/` (to be created, §5) |
| All-pairs pairwise judging + non-bare grading aggregation | `src/fathom/grading/judge.py`, `src/fathom/report.py` |
| Judge validation harness (gold-set + position-consistency) | `src/fathom/grading/judge_validation.py` (to be created, §6) |
| Per-task hard-criteria quality fraction + calibration confusion matrix + crossover | `src/fathom/report.py` |
| Per-band dose-response + (model×effort) cost-quality Pareto (estimated USD) | `src/fathom/report.py` |
| Pilot discrimination/effort-sensitivity protocol + recorded gate | `tasks/model-tier-v1/README.md` (to be created, §9) |
| Calibration report + recommendation back to `model-tiers` | `docs/reports/2026-06-16-model-tier-calibration.md` (to be created, §10) |
| Per-spawn budget cap threaded through the run | `src/fathom/cli.py`, `src/fathom/adapters/claude_cli.py` |

## Numbered sections

### §1 ADR-0007 — calibration study design
Write `docs/adr/0007-model-tier-calibration.md` recording the load-bearing decisions and rejected alternatives: (a) the **two-knob framing** (model = capacity, effort = thinking; the mapping manages only the first); (b) the **calibration quality metric is the verifier fraction over designated HARD criteria** — each task declares ≥2 HARD (capability-gated) criteria, and `quality(task, arm) = (# true HARD criteria) / (# HARD criteria)`, a scalar in [0,1], so one genuine capability failure always exceeds ε instead of being diluted by many easy criteria (VR-7); the full criteria set still feeds the per-criterion table and dose-response, but the calibration scalar is hard-criteria-only — NOT the all-truthy AND that `verifier.py` exit-code and `report.py` `_is_pass` use, and NOT the ordinal judge; (c) **"right tier" = the cheapest model whose mean HARD-criteria quality fraction is within ε of the best model's on that task**, with **ε = 0.10 in fraction units** AND a Wilson-CI overlap check **computed on HARD criteria pooled across the task's trials** (successes = Σ true HARD criteria, n = Σ total HARD criteria over a model's trials on that task → `wilson_interval(successes, n)`; the per-trial mean fraction is the point estimate, the pooled proportion is the CI basis — a raw mean of fractions has no integer count and thus no Wilson CI, FM-N1; the pooled proportion treats correlated criteria as independent, so the CI is a heuristic width, not an exact coverage guarantee, VR-9), so the mapping is *well-tuned* iff predicted tier = empirically-right tier, off-diagonal-below = under-provisioned and off-diagonal-above = over-provisioned, and a tier whose ε-decision rests on overlapping CIs is labeled **indeterminate**, never forced onto the diagonal; (d) the **continuous difficulty ladder** over discrete buckets so the 25/55 boundary placement is testable; (e) **effort staged, not crossed**; (f) the judge as a **validated, ordinal, secondary corroboration** that does not define ε; (g) the **cost axis is a token×price estimate** (subscription auth reports `total_cost_usd=0`, D2) using the pinned `model-tiers` per-1k rates. **Acceptance criterion:** the ADR exists with status Accepted and records, in prose, the hard-criteria verifier-fraction quality metric, the numeric ε, the pooled-criteria Wilson-CI basis (and its independence caveat), the indeterminate-tier rule, the continuous-ladder choice, the staged-effort choice, the judge-as-corroboration choice, and at least one rejected alternative per decision.

### §2 Difficulty-ladder bank with an independent-rater spread gate
Create `tasks/model-tier-v1/` with ≈12 stdlib-Python tasks whose intrinsic difficulty spans 0-100, **genre held ~constant** (all bug-fix / small-feature in small modules) so band differences are difficulty, not task-kind; include rungs **within ±5 of the 25 and 55 boundaries** where well-tunedness is decided. Each task records its series-engine `pr-prompt-scorer` score and predicted tier in a sibling `score.md`. The author's scores are then **re-rated by a second independent rater** (a fresh subagent blind to the intended difficulty) and the **spread acceptance gate** must hold before any spawn: **≥2 tasks scored into each of [0-25], [26-55], [56-100], AND ≥1 task within ±5 of each of 25 and 55, under BOTH raters**; disagreements beyond one band are reconciled or the task is recut. `bank.toml` sets `name`, `dataset_version = "1"`, and a `holdout` of ≥1 sealed task. A **Predicted-signal** block in the README states, per band, the baseline expectation — *does Haiku plausibly pass?* — and the designed-for discrimination (low band ⇒ all three pass, Haiku ceiling confirms the weak tier; high band ⇒ Haiku fails the hard criteria, Opus passes). Because the rubric scores *prompt* complexity, not *model* difficulty — the v3 pilot ceilinged even Opus on high-scored self-contained functions (`tasks/humble-vs-super-v4/V4_NOTES.md`) — each high-band task must name the **concrete capability Haiku is expected to LACK** (e.g. a multi-file root-cause trace, an algorithmic edge case weaker models training-miss), not merely a high score (FM-N3). **Acceptance criterion:** the bank resolves under `fathom run --dry-run`, every task carries two independent recorded scores and a predicted tier, the spread gate holds under both raters (documented in the README), and each high-band task's predicted-signal entry names a concrete capability Haiku is expected to lack (citing the v3/v4 ceiling precedent), with the per-band ceiling/floor risk stated.

### §3 Graded multi-criterion verifiers (partial credit survives)
Each task's `verify.py` emits **multiple escalating booleans** (e.g. `runs`, `basic_correct`, `edge_cases_correct`, `hard_case_correct`, `no_regression`), of which **≥2 are designated HARD** (capability-gated) in the task's `[verify] hard_criteria` list — the calibration quality fraction (§1, §7) is computed over the hard criteria only, so one capability failure exceeds ε rather than being diluted by easy criteria (VR-7). Verifiers keep the repo's existing exit-code convention (exit 0 iff the correctness gate criterion holds). The partial-credit gradient already reaches the ledger — `cli.py` records the criteria dict whenever the trial did not error, and `TrialRecord` persists `verifier_results`, never the pass/fail outcome — so the anti-collapse fix lives entirely in §7's report-side mean-fraction computation, not in verify.py exit codes (FM-N2). Verifiers read only `argv[1]` (the result-view) and carry no scenario/model identity (blindness, ADR-0003). Each task's `[limits] max_turns`/`trial_timeout_s` are sized for the **weakest model's longer, more-iterative runs** (a weaker model loops more on a hard task), so Haiku's hard-band attempts are not truncated into ERRORED and silently dropped, manufacturing a false ceiling (FM-12). **Acceptance criterion:** every task declares ≥2 HARD criteria in `[verify] hard_criteria`; a reference-correct solution passes all criteria and a deliberately-naive solution fails at least one *hard* criterion while passing the basic ones; AND a unit test confirms the emitted criteria dict (including the false hard criterion) is the structure recorded to `verifier_results` — graded-ness proven and the partial-credit gradient shown to survive to the ledger.

### §4 Model-arm scenarios
Author three scenario TOMLs in `scenarios/model-tier/` — `haiku`, `sonnet`, `opus` — identical in `effort = "high"`, allowlist, strategy (`single-session`), and limits, differing **only** by `model` (the pinned `model-tiers` aliases). No arm is named `bare`; the §7 report view must therefore not depend on `report.py`'s bare-anchor pairwise block, which will correctly no-op here (FM-11). Limits are sized per §3 (weakest-model runs). **Acceptance criterion:** `fathom run model-tier-v1 --scenarios-dir scenarios/model-tier --dry-run` resolves all three arms and prints the trial count and USD ceiling, and the three resolved configs differ only in the `model` field (`model_id` resolves to None at author time — deferred to run time — so the hash differs by the `model` string, FM-N6).

### §5 Staged effort-layer scenarios (probed before authored)
Before authoring, run a **1-spawn live acceptance probe** that `claude --effort xhigh` and `--effort max` return non-error on the target model (a 400 would void the layer, FM-7). Then author effort-variant scenarios in `scenarios/model-tier/` that hold model fixed and vary `effort`, restricted to the **substitution cells** — at minimum `sonnet` at `xhigh` (vs `opus` at `high`) and `haiku` at `xhigh` (vs `sonnet` at `high`) — capped at `xhigh` (one optional `max` ceiling probe). These arms are **gated**: run only if the pilot (§9) shows effort moves quality on the mid/high bands; otherwise authored-but-not-run and the report records "effort weak, model dominates." **Acceptance criterion:** the live probe result is recorded, the effort-layer scenarios resolve under `--dry-run` differing from their model-twin only in `effort`, and §9 records the run/skip decision with the pilot evidence behind it.

### §6 All-pairs pairwise judge + validation (secondary, deferrable)
Light the judge as **net-new plumbing** (FM-1/FM-8): a post-`run_matrix` judging pass that reads result-views from the ledger, builds **all three model pairs per task** (Haiku-Sonnet, Sonnet-Opus, Haiku-Opus), calls `judge_pairs` blind (identity-stripped, order swapped and averaged), and appends `GradingRecord`s; plus a **new non-bare aggregation** in `report.py` (the existing one only aggregates against the `bare` anchor). **Orientation convention** (the existing report maps verdict `b`→win against a now-absent bare anchor): order each pair as `(cheaper_model, dearer_model)` so a `b`-win reads as "the dearer model judged better" (FM-N7). Add `src/fathom/grading/judge_validation.py` that, before any verdict cites the judge, measures (a) **gold-set agreement** on known-good vs known-bad reference solutions and (b) **position-consistency** (winner stable under order swap), trusting the judge only if both clear thresholds recorded in the module. This axis is **secondary and deferrable**: the calibration verdict rests on the verifier fraction (§7), so if validation fails or it is descoped for budget/time, the report runs verifier-only and marks the judge axis untrusted/deferred — without invalidating the verdict. **Acceptance criterion:** `judge_validation` runs offline on fixtures, reports gold-set agreement and a position-consistency rate, a unit test shows it *rejects* a position-biased stub judge and *accepts* a faithful one, and a unit test shows the all-pairs aggregation renders a 3-way (no-`bare`) grading ledger without a bare anchor.

### §7 Report — verifier-fraction confusion matrix + crossover
`src/fathom/report.py` gains a per-task **mean hard-criteria quality fraction** per arm (the hard criteria declared in each task's `[verify] hard_criteria`, §3) and a calibration view: **predicted tier** (from the recorded score) vs **empirically-right tier** (cheapest model within ε=0.10 AND Wilson-overlap of the best, per §1), rendered as a confusion matrix with off-diagonal direction labeled and **indeterminate** cells marked where the ε-decision rests on overlapping CIs (FM-10); plus a **crossover-vs-threshold** line — the complexity score at which the empirically-right model steps up — compared against 25 and 55. The matrix is computed from the verifier fraction only; the judge does not enter it (FM-6). **Acceptance criterion:** `fathom report model-tier-v1` renders the confusion matrix (with indeterminate cells possible) and the crossover comparison, and a unit test feeds a synthetic ledger with a known fraction pattern and asserts the matrix cells, the indeterminate labeling on an overlapping-CI case, and the crossover scores.

### §8 Report — dose-response + cost-quality Pareto
`report.py` gains, per difficulty band, the **dose-response**: mean quality fraction and mean cost (tokens and the token×price USD estimate, FM-13) for Haiku→Sonnet→Opus, with Δquality and Δcost per upgrade step and a Wilson CI on the quality deltas; and a **(model×effort) cost-quality Pareto frontier** flagging the non-dominated points (≥ quality AND ≤ estimated cost). **Acceptance criterion:** `fathom report model-tier-v1` renders the per-band dose-response table and the Pareto frontier, and a unit test asserts the frontier on a synthetic set is exactly the non-dominated points (a dominated point is never flagged) — closing the prior bank's false-Pareto-flag defect with a real assertion.

### §9 Pilot gate — quantitative discrimination + effort sensitivity
Document and run a cheap pilot (≈4 tasks spanning the range × 3 models, with **≥5 repeats per model on the high-band tasks** — n=2 cannot resolve a 60%/80% rate, it only yields 0/50/100% (FM-N4) — and 2 repeats on the rest, plus the §5 effort probe) in `tasks/model-tier-v1/README.md`. The **GO predicate is quantitative and two-sided** (FM-4): proceed to the full matrix only if the pilot shows **≥1 high-band hard criterion where Haiku's pass-rate ≤ 60% AND Opus's ≥ 80%**, evaluated only on criteria with **≥5 trials per model** (a measured separation, not merely "criteria vary"); if not met, ADJUST (harden tasks) before any full spend. The pilot also records whether effort visibly moves quality (the §5 run/skip gate) and verifies truncated trials are recovered from the ledger, not dropped (FM-12). **Acceptance criterion:** the README records the pilot's per-arm pass-rates, the explicit GO/ADJUST decision tested against the two-sided predicate (evaluated only on criteria with ≥5 trials/model), the effort layer run/skip decision, and confirmation that no pilot trial was silently dropped as ERRORED.

### §10 Calibration report + recommendation to model-tiers
Author `docs/reports/2026-06-16-model-tier-calibration.md` with experiment, methodology, results (confusion matrix, dose-response, Pareto, crossover, effort finding), threats to validity (including the n=5 directional caveat, the ε/indeterminate handling, and the pooled-criteria-CI independence assumption, VR-9), and conclusion; and a concrete, evidence-backed **recommendation back into the series engine's `model-tiers`** (pinned `1c2748f`) — keep/move the 25 and 55 thresholds, and whether to add effort guidance per band — filed as a fathom-side report plus a series-engine feedback report. **Acceptance criterion:** the report exists with all named sections populated from the run's ledger and states an explicit verdict ("mapping well-tuned" / "threshold X should move to Y") with the confusion matrix and crossover evidence cited and the small-n caveats stated.

### §11 Thread the per-spawn budget cap through the run
`run_matrix` / `_default_runner_factory` in `src/fathom/cli.py` gain an optional per-spawn `max_budget_usd` threaded to `ClaudeCliRunner` (today the runner's `default_max_budget_usd = 5.0` is never overridable from the CLI, so the DoD's "set the cap from pilot cost" had no seam, FM-N5), exposed as a `--max-budget-usd` CLI flag. **Acceptance criterion:** `fathom run ... --max-budget-usd 1.5` constructs the runner with that per-spawn cap (a stub-only test asserts the value reaches `ClaudeCliRunner`), and omitting the flag preserves the existing 5.0 default.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |
| PR05 | §5 | yes |
| PR06 | §6 | yes |
| PR07 | §7 | yes |
| PR08 | §8 | yes |
| PR09 | §9 | yes |
| PR10 | §10 | yes |
| PR11 | §11 | yes |

## Definition of Done (this spec)

- The `model-tier-v1` bank (≈12 tasks + ≥1 sealed holdout) resolves; `fathom run --dry-run` prints the
  trial count and USD ceiling for the three model arms; every task carries two independent scores and a
  predicted tier; the §2 spread gate holds.
- `uv run fathom smoke` passes (current baseline 8/8); the stdlib suite passes — baseline = the item count from `uv run pytest --co -q` recorded at build start
  (STATUS cites 387; CLAUDE.md's 308 is stale — re-derive, don't trust the prose number, VR-8) plus the new §3 graded-ness, §6 judge-validation +
  non-bare-aggregation, §7/§8 report-view, and §11 budget-cap tests (FM-N8).
- The pilot (§9) is run and its **quantitative** GO predicate + effort-sensitivity decision are recorded
  **before** the full spend; the full matrix runs only on a GO.
- **Operational recipe (FM-9), not "chunked":** run with `PYTHONIOENCODING=utf-8` (the cp1252 crash
  fix), in `--limit N` batches sized to fit inside a subscription-token TTL window, `uv run fathom smoke`
  at every resume, and the per-spawn budget cap set from the pilot's observed cost via §11's new plumbing
  (the CLI only *prints* a per-trial ceiling; the real guard is `ClaudeCliRunner.default_max_budget_usd`,
  which §11 threads through `run_matrix`, FM-N5).
- The judge is either validated-and-trusted (§6 thresholds cleared) or the run falls back to verifier-only
  with the judge axis explicitly marked untrusted/deferred — no silent trust; the calibration verdict
  does not depend on it.
- `fathom report model-tier-v1` renders the verifier-fraction confusion matrix (indeterminate cells where
  CIs overlap), crossover-vs-threshold, per-band dose-response, and (model×effort) Pareto frontier.
- `docs/reports/2026-06-16-model-tier-calibration.md` states the well-tuned verdict and the threshold/
  effort recommendation, with CIs and the ceiling/floor + n=5-directional caveats stated.
- A dogfooding feedback report under each registered tool's feedback dir for the tools this work exercised
  (fathom, keel, convoy, craft-collection).

## Pre-mortem certification

*The externalized correctness pass (`pre-mortem-prompt.md`), signed by a fresh reviewer who did NOT
author this spec. `keel check-ready` does not pass until the verdict is `CERTIFIED` (ADR-0002). A freshly-
scaffolded spec is, correctly, not Ready.*

- **Reviewer:** keel:pre-mortem-review (rounds 1-4, 2026-06-16) — fresh non-author reviewers; round 1 NEEDS-REVISION (4 blockers), round 2 NEEDS-REVISION (new blocker FM-N1 + 4 majors), round 3 NEEDS-REVISION (new major VR-7), round 4 CERTIFIED.
- **Verdict:** CERTIFIED
- **Date:** 2026-06-16
- **Reviewed against:** spec round-3-folded state; fathom HEAD `fb1dc38`; mapping-under-test pinned to the series engine `0.8.1` / `1c2748f3004c7c32e67b9379944b92e3777020a6`; grounded in `src/fathom/{scenario,report,ledger,cli,taskbank}.py`, `src/fathom/grading/{judge,verifier}.py`, `tests/test_report.py`, `tasks/humble-vs-super-{v3,v4}/`.
- **Post-fold coherence:** VR-7/8/9 applied consistently across §1, §3, §7, §9, §10 and the DoD; the hard-criteria quality fraction is coherent end-to-end (metric §1(b) ↔ task declaration §3 ↔ ε/Wilson basis §1(c) ↔ confusion matrix §7 ↔ GO predicate §9); the 11↔11 manifest bijection and all four invariants (blindness, append-only ledger, spawn isolation, sealed holdout) re-verified clean.
- **Failure modes considered & folded in:** calibration-fraction-diluted-by-easy-criteria (VR-7) · test-baseline-trusted-from-stale-prose (VR-8) · pooled-Wilson-independence-uncaveated (VR-9) · ceiling-tasks-not-model-hard (FM-3/FM-N3) · weak-model-truncation→false-ceiling (FM-12) · one-sided/non-quantitative-GO-predicate (FM-4) · underpowered-pilot-n=2 (FM-N4) · judge-mistaken-for-a-wiring-tweak (FM-1/FM-8) · judge-orientation-vs-absent-bare-anchor (FM-N7) · borderline-cells-forced-onto-diagonal (FM-10) · cost_usd_est=0-under-subscription (D2/FM-13) · budget-cap-unreachable-from-CLI (FM-N5) · effort-xhigh/max-unproven-on-live-spawn (FM-7) · bank-run-without-scenarios-dir (FM-9) · Pareto-false-positive-on-dominated-points (§8) · engine-bypassPermissions-vs-classifier→direct-execution (Execution note). Three advisory follow-ups (hard-criteria upper bound; §7 score source; §8 strict-domination) logged, non-blocking.

### Fold ledger

| Finding | Target section | artifact:line | Confirmed |
|---|---|---|---|
| FM-1 judge hard-wired to a 2-way bare anchor (no bare arm here) | §6 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:155` | §6 builds all-pairs judging + a new non-bare aggregation; judge demoted to deferrable secondary |
| FM-2 quality scalar not what verifier/report emit; ε undefined | §3/§7 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:158` | quality = verifier fraction computed report-side; criteria already reach the ledger via verifier_results |
| FM-3 rubric structurally avoids the 25/55 boundary rungs | §2 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:143` | independent second-rater + spread gate forcing boundary rungs within ±5 of 25/55 under both raters |
| FM-4 §9 GO gate too weak ("criteria vary") | §9 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:164` | quantitative two-sided predicate: Haiku ≤60% AND Opus ≥80% on a high-band hard criterion |
| FM-5 series-engine scorer/model-tiers SHA unpinned | Grounding | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:34` | pinned to the series engine 0.8.1 @ 1c2748f with thresholds/aliases recorded inline; re-verified at build |
| FM-7 xhigh/max effort unproven on a live spawn | §5 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:152` | §5 requires a 1-spawn live xhigh/max acceptance probe before the effort layer is authored |
| FM-9 "chunked" too vague for the token-TTL/cp1252 risk | Definition of Done | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:199` | concrete recipe: UTF-8 stdout, --limit batches, smoke at resume, per-spawn budget cap |
| FM-12 weak-model truncation → ERRORED → dropped → false ceiling | §3 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:146` | limits sized for the weakest model's longer runs; truncated trials recovered from the ledger |
| FM-N1 Wilson CI uncomputable on a mean-of-fractions | §1 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:140` | CI pooled over criteria (successes = Σ true, n = Σ total) → wilson_interval(successes, n) |
| FM-N4 pilot n=2 cannot resolve the 60%/80% predicate | §9 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:164` | ≥5 repeats/model on high-band pilot tasks; predicate evaluated only on ≥5-trial criteria |
| FM-N5 per-spawn budget cap not threadable from the CLI | §11 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:170` | new §11 threads max_budget_usd through run_matrix + a --max-budget-usd flag |
| VR-7 calibration fraction diluted by easy criteria | §1/§3 | `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md:140` | quality fraction + ε computed over ≥2 designated HARD criteria so one capability failure exceeds ε |
