# Spec — fathom v1 build (spine + series-engine question)

- **Date:** 2026-06-10
- **Status:** ready (DoR passed 2026-06-10 — `keel check-ready` OK, pre-mortem CERTIFIED)
- **Audience:** per-PR implementing agents under the keel method (series engine or in-session executor); the reviewer; the pre-mortem reviewer.
- **Output artifact(s):** `src/fathom/**`, `tests/**`, the series-engine bank under `tasks/`, `scenarios/*.toml`, the series-engine bank ledger under `ledger/`, its rendered scorecard under `report/`

## Context

fathom measures whether an AI coding tool is worth using: it scores task results
blind to scenario, compares scenarios (bare agent / single long session /
the series engine's multi-session series), and joins the comparison with per-run economy
into longitudinal verdicts. The approved design is
`docs/specs/2026-06-10-fathom-v1-design.md`; the verified prior-art base is
craft-collection's `docs/research/2026-06-10-tool-effectiveness-eval-prior-art.md`.
Decisions with alternatives are recorded in
`docs/adr/0001-subscription-cli-behind-vendor-abstract-runner.md`,
`docs/adr/0002-trial-run-append-only-ledger.md`,
`docs/adr/0003-blind-result-only-scoring.md`,
`docs/adr/0004-vendor-claude-runner-core.md`, and
`docs/adr/0005-sealed-holdout-tasks.md`.

Engine facts grounding §6 (verified in the series engine's source, 2026-06-10, and
re-verified by the pre-mortem): the series engine is invoked as
its `run <series.toml>` command; it spawns the `claude` CLI via subprocess with
`--output-format json` and inherits `CLAUDE_CONFIG_DIR` from its environment —
but env inheritance is only half of isolation: the engine's series.toml defaults
include `permission_mode = "bypassPermissions"`, a strong-tier model, max effort,
and its own per-spawn budgets, so every engine config field §6 names must be
pinned explicitly rather than defaulted. The canonical per-spawn usage record is
the `SUBAGENT_COMPLETE` event in `tracker.jsonl` — other events (e.g. IMPL_META)
echo `cost_usd` for context and tracker files accumulate events across engine
invocations, so run records are taken only from `SUBAGENT_COMPLETE` events whose
run id matches the current invocation. Series runs carry weaker pins than
adapter runs (no cache-token split; the recorded model is the requested string,
not the CLI-reported id) — the ledger marks this. The engine requires real
series assets at preflight (per-PR prompt files, a review prompt, an outputs
path, an existing base branch) and operates on local git only (worktrees,
branches, local merges — no GitHub dependency), so trial workspaces must be git
repositories with an initial commit on a pinned branch name.

## Goal

Ship the fathom spine and answer one real question end-to-end: on a 3–5 task bank,
does the **series engine's pipeline** (human-authored decomposition + per-PR gates +
review/fix subagents, multi-session) beat a single long session and a bare-agent
control, at what economy cost — with a resumable committed ledger and a scorecard
to show for it. The pipeline arm differs from the single-session arm by more
than session count (decomposition, gates, review/fix loops, engine settings);
the scorecard names these deltas explicitly (§9) so the verdict claims only what
the comparison supports.

## Gate commands

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`
- Stdlib path for the core: each `tests/test_*.py` marked stdlib-runnable must
  pass via `python tests/test_<name>.py` with no third-party imports.
- `fathom smoke` (after §11 exists) must pass before any paid matrix run.

## Non-goals

- OTel stamping, collector, telemetry join (v2; economy comes from CLI
  stream/result JSON).
- Trigger-axis (recall/specificity) migration from craft-collection.
- keel task bank; non-Claude adapters (the protocol ships, only `claude-cli`
  implements it); Docker workspace isolation; retiring craft-collection `evals/`.
- Judge validation studies; v1 prefers verifier-only grading and the judge path
  ships dark (exercised by tests, not by the v1 verdict) unless a rubric axis
  proves necessary.

## Invariants touched

- **Model calls only via Runner adapters** — `docs/adr/0001-subscription-cli-behind-vendor-abstract-runner.md`.
  Documented exception: the series engine subprocess in
  `src/fathom/strategies/series.py` is the one sanctioned non-adapter
  model-call path (the engine spawns `claude` itself); the review grep treats it
  as the named waiver, never a silent one.
- **Ledger files are append-only; task IDs are stable** — `docs/adr/0002-trial-run-append-only-ledger.md`
- **Scoring inputs are scenario-blind** — `docs/adr/0003-blind-result-only-scoring.md`
- **Spawn isolation properties (credential-only temp config; default-deny tools)** — `docs/adr/0004-vendor-claude-runner-core.md`
- **Holdout sealing** — `docs/adr/0005-sealed-holdout-tasks.md`

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| model-calls-only-via-runner | review-only | review checklist item; grep for subprocess model calls outside `src/fathom/adapters/`, with `src/fathom/strategies/series.py` recorded as the one sanctioned engine-boundary exception |
| ledger-append-only | review-only | code shape (append + tolerant reader); edit-time hook is a named future candidate (`docs/method/method-bindings.md`) |
| stable-task-ids | review-only | dataset_version bump rule in bank manifest; review checklist item |
| scenario-blind-scoring | review-only | verifier/judge interfaces take no scenario identity (§7, §8); review checklist item |
| spawn-isolation | planned | `fathom smoke` (§11) asserts on real spawns, including the engine-boundary assertion that an engine-driven spawn carries no bypass flag; required before paid runs and at every resume (§13) |
| holdout-sealing | review-only | bank manifest holdout list (§12); report separation (§9) |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| Trial/run/grading records, resume keys, tolerant reader | `src/fathom/ledger.py` — to be created (§2) |
| Bank manifest, task loading, fixture staging, holdout split | `src/fathom/taskbank.py` — to be created (§3) |
| Scenario resolution, version pins, config hash | `src/fathom/scenario.py` — to be created (§4) |
| Scenario definitions (bare, single-long-session, series) | `scenarios/` — to be created (§4) |
| Runner protocol + RunRecord | `src/fathom/adapters/base.py` — to be created (§5) |
| Subscription Claude CLI adapter (vendored core) | `src/fathom/adapters/claude_cli.py` — to be created (§5) |
| StrategyExecutor protocol | `src/fathom/strategies/base.py` — to be created (§6) |
| Single-session executor | `src/fathom/strategies/single_session.py` — to be created (§6) |
| series executor (tracker.jsonl → run records) | `src/fathom/strategies/series.py` — to be created (§6) |
| Deterministic verifier execution | `src/fathom/grading/verifier.py` — to be created (§7) |
| Swap-order pairwise judge | `src/fathom/grading/judge.py` — to be created (§8) |
| Scorecard rendering, Wilson CI, economy table | `src/fathom/report.py` — to be created (§9) |
| CLI entry (`fathom run`/`report`/`smoke`, dry-run, limits) | `src/fathom/cli.py` — to be created (§10) |
| Real-spawn isolation smoke gate | `src/fathom/smoke.py` — to be created (§11) |
| v1 task bank (tasks, fixtures, verifiers) | the series-engine bank under `tasks/` — to be created (§12) |
| v1 committed ledger | `ledger/` — to be created (§13) |
| v1 rendered scorecard | `report/` — to be created (§13) |

## Numbered sections

### §1 Project scaffold
uv project with src-layout (`src/fathom/`), ruff and pytest configured, empty
package with a placeholder stdlib-runnable test, `.gitignore` covering `report/`
and workspace temp dirs, README stub naming the project's purpose and the gate
commands. **Acceptance criterion:** `uv sync` succeeds and all three gate
commands pass on the fresh checkout; the placeholder test also passes via
`python tests/test_placeholder.py`.

### §2 Ledger
Append-only JSONL ledger in `src/fathom/ledger.py`: dataclasses for trial, run, and
grading records with the version-pin fields from
`docs/adr/0002-trial-run-append-only-ledger.md`; append and iterate operations;
resume-key computation `(bank, dataset_version, task_id, config_hash, repeat)`;
tolerant reader.
**Acceptance criterion:** stdlib-runnable unit tests show round-trip of all three
record kinds, resume-set computation that skips completed tuples, and a malformed
line being skipped with a warning while later lines still load.

### §3 Task bank loader
In `src/fathom/taskbank.py`: parse `bank.toml` (name, dataset_version, holdout
list) and per-task `task.toml`
(stable id, instruction, limits, verify entry); stage a task's `fixtures/` into a
fresh temp workspace and initialize it as a git repository with an initial commit
on an explicitly pinned branch name (`git init -b <base>`, matching the series
template's base branch — never the host default) and with `core.autocrlf=false`
set on the staged repo. **Acceptance criterion:** unit tests load a sample bank
from test fixtures, reject duplicate task ids and missing manifest fields with
named errors, parse the holdout list, and produce a staged workspace that is a
git repo with the fixture content committed on the pinned branch with
`core.autocrlf=false`.

### §4 Scenario resolution
In `src/fathom/scenario.py`: parse `scenarios/*.toml` (adapter, model, strategy,
tool source, limits); resolve
pins at run time (exact model id as reported by the CLI, tool repo git SHA, and —
for `tools.source = "repo"` — the explicit tool invocation command, e.g.
`uv run --project <repo> <engine>`, never a bare PATH lookup); compute
`config_hash` over the canonicalized resolved scenario including the invocation
command. The scenario schema carries an explicit `effort` field pinned to the
same value across all three v1 scenarios (parity across arms) and may override
per-task trial limits (strategy-aware timeouts). Ship the three v1 scenario
files: `bare`, `single-long-session`, `series`.
**Acceptance criterion:** unit tests show config_hash is stable under TOML key
reordering and changes when any resolved pin (including the tool invocation
command) changes; the three committed scenario files parse, resolve against a
stub resolver, and declare equal `effort` values.

### §5 Runner adapter (vendored core)
`Runner` protocol and `RunRecord` in `src/fathom/adapters/base.py`; vendor the
craft-collection spawn core into `src/fathom/adapters/claude_cli.py` per
`docs/adr/0004-vendor-claude-runner-core.md`: temp `CLAUDE_CONFIG_DIR` with
copied credential only, headless default-deny (the *absence* of any
permission-mode flag — `bypassPermissions` is never passed), explicit
allow/disallow lists, stream-json parsing with partial-stream tolerance, retry
with cap, per-spawn budget and turn flags, and the `--effort` flag resolved from
the scenario (cross-arm parity with the engine, which always passes effort;
judge calls inherit it via the Runner). Auth failures and subscription
usage-limit responses are classified as **infrastructure errors**, distinct from
task errors — they must not score or consume a trial's error-retry budget.
**Acceptance criterion:** with subprocess stubbed, unit tests show the adapter
builds the isolation environment exactly (credential-only temp config, absence
of `--permission-mode` and `--dangerously-skip-permissions`, the exact
`--allowed-tools`/`--disallowed-tools` lists, and the resolved `--effort`
flag), parses both a complete and a
truncated stream-json fixture into RunRecords with usage/turns/duration/cost
fields, honors the retry cap, and classifies an auth-failure fixture and a
usage-limit fixture as infrastructure errors.

### §6 Strategy executors
`StrategyExecutor` protocol in `src/fathom/strategies/base.py`;
`src/fathom/strategies/single_session.py` (one Runner call per trial);
`src/fathom/strategies/series.py`: instantiate the task's committed
series assets (§12) **outside the trial workspace** — the instantiated
series.toml, prompt files, review prompt, and the engine outputs directory live
in a sibling temp directory and are referenced by absolute paths, so no engine
input or output asset ever sits inside the scored workspace — **pinning every
engine config field the comparison depends on rather than accepting engine
defaults** — `permission_mode` set to a
non-bypass mode with the same allow/disallow philosophy as the other arms (the
engine's own default is `bypassPermissions` and is never accepted), model and
`effort` and per-spawn budgets mapped from the resolved scenario, parallelism
off — then invoke the scenario's pinned tool invocation command
(the series engine's `run <series.toml>`) as a subprocess with the trial workspace as cwd
and the trial's `CLAUDE_CONFIG_DIR` exported in its environment. Run records
are materialized as **one record per `SUBAGENT_COMPLETE` event in
`tracker.jsonl` whose run id matches this invocation** (IMPL_META echoes and
foreign-run-id events are ignored), marked with the weaker series pin level,
plus the engine's own wall-clock. Engine failures are classified before
scoring: the executor scans engine output and tracker events for auth and
usage-limit signatures (e.g. retry-exhausted reasons) and reclassifies matching
failures as §5-style infrastructure errors feeding §10's clean stop — the
engine's bare exit code carries no such distinction, so only failures that are
not infrastructure mark the trial errored. On trial timeout the executor
terminates the **entire engine process tree**, not just the direct child.
**Acceptance criterion:** unit tests show single-session yields exactly one run
per trial;
with the engine subprocess stubbed, the series executor emits a series.toml in
the sibling assets directory (absolute paths; outputs directory outside the
workspace) with the pinned non-bypass permission mode and scenario-mapped
model/effort/budgets, passes the isolation env through, materializes records
only from matching `SUBAGENT_COMPLETE` events out of a fixture containing an
IMPL_META echo and a foreign-run-id event, marks the trial errored on a genuine
nonzero engine exit while a stubbed usage-limit engine failure is reclassified
as an infrastructure error (not scored), and on simulated timeout terminates
the whole process tree with no orphan surviving.

### §7 Verifier execution
In `src/fathom/grading/verifier.py`: extract the **scored result view** from the
final trial workspace — the working tree at the final integration tip with
engine output paths excluded (the engine's outputs directory, `tracker.jsonl`,
logs, and its automation gitignore marker), because the workspace itself
otherwise fingerprints the scenario (branch topology, automation commits) — and
run the task's `verify.py` in the harness environment with that result-view path
as its only task argument (no scenario identity in argv or env, per
`docs/adr/0003-blind-result-only-scoring.md`); the exclusion also covers any
engine **input** assets (series config, prompt files) should one appear
in-tree despite §6's outside-the-workspace rule; capture per-criterion JSON from
stdout; nonzero exit with valid JSON is a scored fail, crash or non-JSON output
marks the trial errored. **Acceptance criterion:** unit tests cover all three
outcomes (pass with criteria, fail with criteria, errored on crash or garbage
output), assert the verifier subprocess environment and argv contain no scenario
identifier, and include the blindness fixture: a bare-style and a series-style
workspace with identical code — the series-style one containing a stray
instantiated engine asset — yield byte-identical verifier input.

### §8 Pairwise judge
Port the swap-order pairwise judge to `src/fathom/grading/judge.py`: both A/B
orders per pair, win only when both
orders agree, else tie; pairs match by repeat index; the judge call goes through
the Runner with tools disabled and a strict-JSON rubric prompt; grading records
carry resolved judge model and judge config hash. The A/B payload is defined,
not left to the implementer: the §7 scored result view rendered as a unified
diff against the task's fixture baseline, size-capped with a recorded
truncation marker. **Acceptance criterion:** stdlib-runnable unit tests with a
stubbed Runner cover agreement, disagreement (tie), and repeat-index pairing,
and assert the judge prompt contains the A/B result-view diffs but no scenario
names.

### §9 Report
In `src/fathom/report.py`: `fathom report <bank>` renders `report/scorecard-<bank>.md`
from the ledger alone: per-scenario verifier pass-rate with Wilson 95% CI (port
the existing interval math), pairwise win/tie/loss vs the bare anchor when
grading records exist, economy table (tokens, turns, wall-clock, sessions per
trial, estimated USD), holdout section separated, one verdict line per scenario.
Every verdict line prints its n and the Wilson CI with a "directional, not
final" qualifier, and the series-engine-pipeline verdict line enumerates the arm
deltas (human decomposition, per-PR gates, review/fix subagents, engine
settings) so the claim never exceeds the comparison. **Acceptance criterion:** a
golden-file test renders the expected scorecard from a fixture ledger covering
all three scenarios including a multi-run trial — verdict lines carrying
n/CI/qualifier and the arm-delta enumeration — and re-running the report is
byte-identical (idempotent).

### §10 CLI
In `src/fathom/cli.py`: `fathom run <bank>` (scenario matrix × non-holdout tasks ×
repeats, honoring
resume), `fathom report <bank>`, `fathom smoke`; `--dry-run` prints the planned
trial/spawn counts and the cost ceiling and spawns nothing; `--limit` caps
trials; every paid entry point prints the upfront ceiling before spawning. An
infrastructure error from any executor (auth failure, usage limit — §5, §6)
stops the matrix cleanly: the affected trial is not scored, the run exits with a named
infrastructure status, and the ledger remains the resume checkpoint.
**Acceptance criterion:** unit tests with stubbed executors show dry-run spawns
nothing while printing counts and ceiling, limit caps the planned set, a second
run over a completed ledger plans zero trials, and a stubbed usage-limit error
stops the matrix without scoring the affected trial.

### §11 Smoke gate
Port the real-spawn smoke assertions to `src/fathom/smoke.py` (`fathom smoke`): the
credential-only temp
config spawn is authenticated and completes; a disallowed tool call is refused
under default-deny; stream parsing detects activity; plus the engine-boundary
assertion: a minimal one-PR engine invocation against a scratch workspace
confirms the §6-pinned non-bypass permission mode actually reaches the engine's
spawned CLI invocation (no bypass flag in the spawn). Exit nonzero on any
violation. **Acceptance criterion:** running `fathom smoke` on this machine
performs the real-spawn and engine-boundary assertions and reports all passing,
and the command exits nonzero when any assertion fails (demonstrated with a
forced-fail flag or fixture).

### §12 series-engine task bank
Author 3–5 realistic Python tasks in the series-engine bank under `tasks/` at the coordination
threshold (multi-file feature or fix where decomposition into a series plausibly
helps): per task a git-initializable fixture skeleton, instruction, limits, and a
deterministic `verify.py`; exactly one task marked holdout in `bank.toml`. The
bank also owns each task's **series assets** — the committed `series.toml`
template, a `prompts/` directory with one prompt file per series PR, and the
review prompt — because the per-PR decomposition is part of the treatment being
measured; series assets are covered by the dataset_version bump rule like any
other task content. Task limits are strategy-aware: the series arm gets a
per-scenario trial-timeout override sized so one engine subagent allowance
cannot exceed the trial budget. Bank-authoring rule (blindness): verifiers
never read git metadata or automation directories — only the scored result view
(§7). **Acceptance criterion:** a bank-validation test demonstrates every
verifier passes on its reference solution and fails on the unmodified fixture,
the bank manifest parses with exactly one holdout task, and every task ships
complete series assets (series.toml template, one prompt per PR, review prompt)
that pass the engine's preflight checks against a staged fixture workspace AND
whose baseline gate sweep passes non-dry on the unmodified staged fixture (or
the template sets `baseline_strict` explicitly with recorded rationale) — the
task's deliberately-failing acceptance tests must live in the verifier, never
in the engine's gate commands, or every series trial aborts at baseline.

### §13 v1 paid run
Execute the full matrix (3 scenarios × non-holdout tasks × default repeats 2)
under budget guards; demonstrate resume by interrupting once and re-invoking
(zero completed trials re-spawned); `fathom smoke` runs before the first spawn
**and again at every resume** (auth and usage-limit state decay over a
multi-hour matrix); render the scorecard into `report/`; commit the ledger under
`ledger/`.
**Acceptance criterion:** the committed ledger and rendered scorecard exist for
the full matrix; the interrupt-resume demonstration (including the smoke re-run
at resume) and the verdict lines are recorded in the run notes
(`docs/reports/`), satisfying the design doc's done criteria 1, 4, and 5.

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
| PR12 | §12 | yes |
| PR13 | §13 | yes |

## Definition of Done (this spec)

- All thirteen PRs merged with the project DoD checklist
  (`docs/method/definition-of-done.md`) green per PR.
- The five v1 done-criteria in the design doc
  (`docs/specs/2026-06-10-fathom-v1-design.md`, "v1 is done when") are demonstrated,
  not asserted: resumable matrix, smoke gate before paid runs, stdlib-runnable
  core tests, a full paid run with scorecard verdict, committed ledger surviving
  a second appending run.
- A reflection pass (`docs/method/reflection-triage.md`) has run over the series
  and any recurring trap is promoted (checklist item, guardrail, or
  spec-template change).
- fathom is registered in the operator's feedback-targets table so future sessions
  report into the local, gitignored `feedback/` dir.

## Pre-mortem certification

*The externalized correctness pass (`docs/method/pre-mortem-prompt.md`), signed by
a fresh reviewer who did NOT author this spec.*

- **Reviewer:** keel pre-mortem-review subagent (two blind passes: full pre-mortem + certification, then re-certification; non-author)
- **Verdict:** CERTIFIED
- **Date:** 2026-06-10
- **Post-fold coherence:** Certifying reviewer re-read §4–§7, §10, §12, the Context engine-facts paragraph, and the Enforcement table; reconciled each fold across its prose/acceptance pairs and cross-references (effort declared §4 / transmitted §5 / mapped §6; sibling-assets rule §6 with §7 stray-asset exclusion and fixture; §12 baseline-pass vs verifier-fail coexistence; §5/§6 infrastructure classification feeding §10's any-executor clean stop). No new blocker found.
- **Failure modes considered & folded in:** Round 1 raised FM-1..FM-12 (two BLOCKERs: engine bypassPermissions default; missing series assets at preflight — plus arm-honesty, workspace blindness leaks, timeout/process-tree, tracker double-count, subscription decay, and five MINORs); certification pass found three partial folds and raised FM-13..FM-16 (effort transmission, engine assets outside workspace, baseline gate sweep vs failing fixtures, engine-failure classification); all sixteen folded and verified coherent across two certification passes.
