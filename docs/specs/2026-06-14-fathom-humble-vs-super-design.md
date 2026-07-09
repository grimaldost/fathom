# Spec — fathom plugin-eval: humblepowers vs superpowers

- **Date:** 2026-06-14
- **Status:** certified (round-2 pre-mortem, recorded below) and executed — four analyses shipped on this instrument (v1–v4); index in `docs/STATUS.md`
- **Audience:** fathom maintainer; the keel pre-mortem reviewer; the series-engine decomposer
- **Output artifact(s):** `tasks/humble-vs-super-v1/`, `scenarios/humble-vs-super/`, adapter/scenario/ledger/report changes under `src/fathom/`, `docs/adr/0006-plugin-mount-fidelity.md`

## Context

Measure, with fathom, whether **humblepowers** produces better coding-task outcomes than **superpowers** *as
actually shipped* inside Grimaldo's Claude stack, and at what economy. This is the first **plugin-level,
triggering-inclusive** fathom question: a process-discipline plugin's value is that the right discipline
(TDD, systematic-debugging, verification-before-completion, choosing-tools/using-superpowers) auto-fires at the
right moment, so we mount the whole plugin and let it trigger — not force-load one skill body as
`skill-pyeng-v1` did.

Builds on the v1 spine (`docs/specs/2026-06-10-fathom-v1-design.md`) and its precedent
`docs/specs/2026-06-13-fathom-skill-eval-pyeng-design.md` (per-scenario injection, blind verifier,
per-criterion table). Touches ADR-0001 (vendor-abstract runner), ADR-0002 (append-only ledger), ADR-0003
(blind result-only scoring), ADR-0004 (spawn isolation / vendored runner core), ADR-0005 (sealed-holdout
tasks); adds ADR-0006 (plugin-mount fidelity).

## Spike validation (2026-06-14)

Two real `claude -p` spawns (opus, isolated credential-only config) de-risked the load-bearing assumptions
before this spec was finalized:

- **humblepowers mount confirmed** — init event reports `plugins: humblepowers (source: humblepowers@inline)`
  and `skills:` lists all eight humblepowers skills; `Skill` is among the available tools. The isolated config
  stayed clean — only the mounted plugin appeared; none of the user's other installed plugins leaked. Cost
  $0.49.
- **superpowers mount confirmed** — superpowers is installed nowhere locally, so it was fetched from
  `github.com/obra/superpowers` (v5.1.0, pinned `6fd4507659784c351abbd2bc264c7162cfd386dc`) and mounted via
  `--plugin-dir`: init reports `superpowers@inline` with all 14 `superpowers:*` skills loaded; same built-ins
  common-mode. Cost $0.27. (Resolves the pre-mortem's FM-1 blocker.)
- **Both mounts are model-agnostic at the init layer** — the available-skills list is emitted before any model
  turn, so a mount check reads identically regardless of which model runs (matters for §5).
- **Built-ins are common-mode** — the non-plugin skills present (`deep-research`, `verify`, `code-review`,
  `simplify`, …) are CLI built-ins, identical across every arm including `bare`; they cannot bias the contrast.
- **Conditional auto-fire (design-shaping)** — with TDD available the model *declined to load it*: "the task is
  small … loading the full skill ceremony isn't worth the context cost," then applied TDD from training. So a
  task must clear the model's own *worth-loading bar* or all arms collapse toward `bare` (drives §7's
  operationalized sizing).
- **Allowlist/shell** — the agent reached for the `PowerShell` tool first on Windows; a scoped `Bash(python:*)`
  blocked routine `ls` and burned every turn (drives §8's allowlist).
- **Asymmetry note** — both plugins ship subagent-orchestration skills (humble `planned-execution`; super
  `subagent-driven-development`, `dispatching-parallel-agents`). Decision recorded: `Task` is **allowed** so
  both run as-shipped (disallowing would hobble both, biased against the side with more orchestration).
- **Billing observation** — result events carried real `total_cost_usd`, not the `0` defect D2 reports; this
  set §11 (resolve the billing path and the cost-flow dead-end before a paid matrix).

## Goal

Deliver a runnable `humble-vs-super-v1` bank and the 5-arm scenario set that lets `fathom run`/`report` produce a
blind verdict on **correctness × no-regression × test-discipline × economy** for humblepowers vs superpowers,
with a pre-registered primary contrast and a cost-probe pilot before the full spend.

## Gate commands

All must pass before any commit (project standard, `CLAUDE.md`):

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run pytest`  (stdlib-runnable suite)
- `uv run fathom smoke`  (real-spawn isolation + injection + the new mount/available gate, §5)

Run-planning (spawns nothing): `uv run fathom run humble-vs-super-v1 --scenarios-dir scenarios/humble-vs-super --dry-run`.

## Non-goals

- **Trigger recall/specificity** as a dedicated measurement — owned by `session-workflow:evaluate-skill`. Here
  triggering is included in the outcome, not measured in isolation.
- **Skill-activation capture** as a covariate (which skills fired, load-vs-skip reasoning) — valuable and
  recommended, but a Phase-2 add; the verdict here rests on end-state outcomes.
- **Lighting the pairwise judge** (`src/fathom/grading/judge.py`) — Phase 1 is verifier-only; §10 only hardens
  blindness so the judge can be lit later.
- **A dedicated subagent-orchestration bank** (orchestration as the *primary* variable) — `Task` is allowed
  here so both plugins run as-shipped, but tasks engineered to stress orchestration are a separate question.
- **Network/execution-based grading inside the spawn** — tasks are stdlib-only Python; verifiers run locally,
  offline (fathom constraint C3).

## Invariants touched

- **Blindness** (ADR-0003) — verifiers read only the result-view; §10 hardens it against plugin scaffolding.
- **Append-only ledger** (ADR-0002) — resume key includes `config_hash`, which §2 extends; §11 adds a cost
  field to the ledger record (additive; existing lines unaffected).
- **Spawn isolation** (ADR-0004) — `--plugin-dir` (§3) adds plugins per session without touching the
  credential-only config dir; default-deny preserved (no `bypassPermissions`).
- **config_hash determinism / longitudinal integrity** — §2 folds the mounted plugin set into the hash; new
  decision recorded in ADR-0006 (§1).
- **Stdlib core** — new modules under `src/fathom/` stay stdlib-only (`docs/specs/2026-06-10-fathom-v1-design.md`).

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| Blindness (result-only verifier) | enforced | `src/fathom/grading/verifier.py`; §10 adds scaffolding scrub |
| Append-only ledger | enforced | `src/fathom/ledger.py`; resume key `(bank, dataset_version, task_id, config_hash, repeat)` |
| Spawn isolation (default-deny, credential-only config) | enforced | `src/fathom/adapters/claude_cli.py`; `fathom smoke` |
| config_hash includes mounted plugin set | planned | §2; absent==empty regression test keeps prior ledgers stable |
| Treatment arm armed (plugin skills mounted/available) | planned | §5 real-spawn mount/available smoke check (init-event, model-agnostic) |
| Stdlib-only core modules | review-only | code review; no third-party import in `src/fathom/` |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| Plugin-mount fidelity decision + alternatives | `docs/adr/0006-plugin-mount-fidelity.md` (to be created, §1) |
| `[plugins] mount` scenario field + `(name,version,tree_sha)` hashing | `src/fathom/scenario.py` |
| `--plugin-dir` (repeatable) command assembly | `src/fathom/adapters/claude_cli.py` |
| Mount plumbing + warn-on-missing-mount | `src/fathom/cli.py` |
| Real-spawn mount/available + unmounted-control smoke check | `src/fathom/smoke.py` |
| Bug-fix/regression tasks + blind verifiers | `tasks/humble-vs-super-v1/` (to be created, §6) |
| Small-feature edge-case-trap tasks + blind verifiers | `tasks/humble-vs-super-v1/` (to be created, §7) |
| Vendored pinned plugin copies | `tasks/humble-vs-super-v1/plugins/` (to be created, §8) |
| 5 arm scenarios | `scenarios/humble-vs-super/` (to be created, §8) |
| Efficiency view (quality-per-token, Pareto) | `src/fathom/report.py` |
| Result-view scaffolding scrub | `src/fathom/grading/verifier.py` |
| Billing-path + ledger cost field + economy plumbing | `src/fathom/adapters/claude_cli.py`, `src/fathom/ledger.py`, `src/fathom/cli.py`, `src/fathom/report.py` |

## Numbered sections

### §1 ADR-0006 — plugin-mount fidelity
Write `docs/adr/0006-plugin-mount-fidelity.md`: record the decision to mount whole plugins via `--plugin-dir`
(triggering included) over force-loading skill bodies, to fold the mounted plugin set into `config_hash`, and
the common-mode-cancellation rationale for the held-constant stack (the `stack-*` arms mount an *identical*
held-constant plugin set, so its exact versions cannot bias the humble↔super contrast). **Acceptance criterion:** the
ADR exists with status Accepted and records the rejected force-load alternative and the common-mode argument in
prose.

### §2 Scenario `[plugins] mount` field + config_hash extension
Add `PluginsConfig(mount: tuple[str, ...] = ())` to `ScenarioConfig`/`ResolvedScenario`; absolutize each path
relative to the scenario file; at resolve time compute `(name, version, tree_sha)` per mounted dir and include
a `plugins` key in the hashable dict **only when `mount` is non-empty**. `tree_sha` is the `git write-tree` of
the vendored plugin subtree at its pinned commit over tracked files only (ignore `__pycache__`, `.venv`,
`.git`) so incidental writes never fork the ledger. **Acceptance criterion:** a scenario with a mount hashes
differently from one without; absent-mount scenarios keep the committed series-engine-bank and `skill-pyeng-v1`
config_hashes byte-for-byte stable (regression test); changing a pinned plugin's `tree_sha` changes the hash.

### §3 Adapter `--plugin-dir` wiring
`build_command(..., plugin_dirs: Sequence[str] = ())` appends one `--plugin-dir <d>` per dir in order;
`ClaudeCliRunner` gains the param and `execute` reads it off the resolved scenario. **Acceptance criterion:**
`build_command` with two mounts emits `--plugin-dir A --plugin-dir B` in order, with none emits no
`--plugin-dir` token, verified by stub-only tests (no real spawn).

### §4 CLI factory mount plumbing + warn-on-missing-mount
`cli.py` runner factory reads `scenario.plugins.mount`, passes it to the runner, and prints a loud `WARNING`
(arm flagged unarmed) when a declared mount dir is missing or empty, mirroring the inject K7 warning.
**Acceptance criterion:** a scenario naming a nonexistent mount dir produces the WARNING and marks the arm
unarmed in the run log; a valid mount produces no warning.

### §5 Smoke: real-spawn mount/available + unmounted control
`smoke.py` adds a check group that mounts a tiny canary plugin and asserts, **from the spawn's init event**
(model-agnostic), that its skill is *available/mounted*, and that a control spawn **without** the mount lacks
it. This proves mount, not firing — real auto-fire is exercised by the cost-probe pilot (Definition of Done),
not asserted here. **Acceptance criterion:** `uv run fathom smoke` includes and passes the new group; the check
fails loudly if a mounted plugin's skills are absent from the spawn's init event (the generalized armed gate).

### §6 Bug-fix/regression task pack
Create at least two bug-fix tasks under `tasks/humble-vs-super-v1/` (`fix-offbyone-paginator`,
`fix-tz-dst-normalize`) plus the sealed holdout (`fix-cache-eviction-bug`): each a stdlib project with a
planted subtle bug, a shipped passing suite that does not cover the bug, a hidden bug test, and a blind
`verify.py` grading `fix_correct` + `no_regression` + `regression_test_present` (the candidate's test must fail
against the stashed original source and pass against the candidate's). Each task sets `[limits]
max_turns`/`trial_timeout_s` sized for the *longest* (allow-Task subagent) arm so discipline arms are not
truncated out of the per-criterion table. **Acceptance criterion:** on the untouched fixture the verifier
reports `fix_correct=false`; on a reference correct fix it reports every criterion true; `regression_test_present`
distinguishes a real regression test from none (unit-tested).

### §7 Small-feature edge-case-trap task pack
Create at least two feature tasks (`feature-csv-coalesce`, `feature-retry-backoff`) sized **above the
worth-loading bar** — operationalized as: the reference solution spans ≥2 files or requires a reproducing test
or written plan before the change, so the model's own dispatch rationally loads a discipline rather than
free-handing it. Each has the same explicit `[limits]` sizing as §6 and a blind `verify.py` emitting
per-edge-case booleans plus `tests_present`. **Acceptance criterion:** the verifier emits one boolean per named
edge case; a reference solution passes all and a deliberately naive solution fails at least one edge criterion,
demonstrated in a unit test.

### §8 Vendored pinned plugins + 5 arm scenarios
Vendor pinned copies under `tasks/humble-vs-super-v1/plugins/`: humblepowers 0.3.1 and superpowers
(`github.com/obra/superpowers` @ `6fd4507`, v5.1.0). Author five scenario TOMLs in `scenarios/humble-vs-super/`
(`bare`, `humble-only`, `super-only`, `stack-humble`, `stack-super`), identical in model/effort/allowlist/limits
and differing only by `[plugins] mount`. Because `--plugin-dir` mounts only what is named (spike), the `stack-*`
arms list the held-constant set — `engineering-discipline` and `session-workflow` — as additional explicit
mounts, identical across both, each hashed via §2. The allowlist is
`["Read","Write","Edit","Glob","Grep","Task","PowerShell","Bash"]`: `Task` allowed (both plugins ship subagent
skills); broad `Bash`/`PowerShell` so the agent works naturally (the spike's scoped-Bash turn-burn) — a
deliberate deviation from prior banks' scoped Bash, acceptable in an isolated, network-free temp workspace and
identical across arms (still default-deny, never `bypassPermissions`). **Acceptance criterion:** `fathom run
humble-vs-super-v1 --scenarios-dir scenarios/humble-vs-super --dry-run` resolves all five arms and prints the
trial count and USD ceiling; the two `stack-*` arms' resolved configs differ only by the humble/super directory
within an identical held-constant set.

### §9 Report efficiency view
`report.py` gains an efficiency view: per arm, the per-criterion pass rates plus mean tokens (in/out/cache),
turns, wall-clock, a derived quality-per-100k-tokens, and a Pareto-dominance flag among arms.
**Acceptance criterion:** `fathom report humble-vs-super-v1` renders one efficiency row per arm and flags any arm
that Pareto-dominates another (greater-or-equal quality at less-or-equal tokens).

### §10 Result-view scaffolding scrub
Extend the grading result-view to strip/normalize process-scaffolding paths (`.remember/`, `plans/`,
`docs/plans/`, journal dirs) so a later judge cannot infer the arm; Phase-1 verifiers already key only on the
deliverable. **Acceptance criterion:** given a workspace containing scaffolding directories, the result-view
handed to grading excludes them (unit-tested), and verifier output is identical with or without them present.

### §11 Billing-path resolution + cost-flow repair
Resolve whether matrix spawns bill the copied subscription credential or a passed-through `ANTHROPIC_API_KEY`;
document the intended path. Repair the economy dead-end the pre-mortem found: the adapter parses
`total_cost_usd` into its RunRecord but the *ledger* RunRecord has no cost field, so it is dropped before the
report (the real root cause of D2). Add a `cost_usd_est` field to the ledger record, persist it in `cli.py`, add
a token×price fallback estimate in the adapter parse, and repoint `report.py`'s economy/efficiency columns at
the ledger field instead of the never-emitted `usage['cost_usd']` key. **Acceptance criterion:** a parsed run
with known token counts yields a non-zero `cost_usd_est` in the ledger and `fathom report` renders non-zero USD;
`docs/STATUS.md` D2 records the resolved billing path.

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

- **100 working trials** (5 arms × 4 tasks × 5 repeats) run resumably by `fathom run`; re-invocation re-spawns
  nothing already `completed`. The sealed holdout (5 arms × 1 task × 5 repeats = 25) is **not** run by
  `fathom run` (ADR-0005 / the `cli.py` `non_holdout` filter); it is a post-verdict sealed checkpoint spent only
  after the primary verdict is locked, via a follow-up that promotes the holdout task (no current CLI flag — a
  one-line addition, tracked outside this manifest).
- Before the full spend, a **cost-probe pilot** (≈1 task × 5 arms × 1 repeat, `Task` allowed) confirms that
  treatment plugin skills actually fire, sets the per-trial USD cap from observed subagent cost, and checks that
  `bare` is not already at ceiling. The full run proceeds only if the pilot shows discrimination headroom.
- `uv run fathom smoke` passes including the §5 mount/available gate.
- Stdlib unit tests pass for §2 hashing, §3 command assembly, §6/§7 verifier parsing, §9 efficiency math,
  §10 scrub, §11 cost flow.
- `fathom report humble-vs-super-v1` renders the per-criterion table and the efficiency view. **Pre-registered
  analysis:** the *binding* verdict is humble-vs-bare (large expected effect); humble-vs-super is **exploratory**
  on the pre-registered separating signals — `regression_test_present`, `no_regression`, and the continuous
  economy metrics (tokens/turns), which discriminate at far lower n than binary pass-rates. At ~20 trials/arm a
  binary criterion's Wilson half-width is ~±0.2, so a small humble-vs-super pass-rate gap is reported with its
  interval and not over-claimed; repeats are added on a separating criterion only if the pilot shows a
  resolvable gap.
- Truncated trials (timeout / max-turns) are recovered from the ledger for the run notes, since the per-criterion
  table currently drops them (STATUS reporting gap) and discipline arms run longer.
- A dogfooding feedback report (local, gitignored `feedback/` dir) on fathom's plugin-eval fit, with a cost table.

## Pre-mortem certification

*The externalized correctness pass (`docs/method/pre-mortem-prompt.md`), signed by a fresh reviewer who did NOT
author this spec. `keel check-ready` does not pass until the verdict is `CERTIFIED` (ADR-0002).*

- **Reviewer:** keel:pre-mortem-review (round 2, 2026-06-14) — fresh non-author re-review of the folded spec
  (round 1 returned NEEDS-REVISION with 3 blockers + 9 majors/minors).
- **Verdict:** CERTIFIED
- **Verdict scope:** every round-1 blocker and major is adequately folded; no new blocker found; the five
  advisory follow-ups below do not block.
- **Date:** 2026-06-14
- **Post-fold coherence:** the counts hang together — 100 working trials = 5 arms × 4 tasks × 5 repeats, with the
  25-trial sealed holdout correctly excluded from `fathom run` (the non_holdout filter); arms remain 5; Task-allowed
  is consistent across Non-goals, the §8 allowlist, and the cost-probe-pilot gate; §5 is named "mount/available"
  uniformly across the enforcement table, concept map, and the section; every scope-narrowing finding (trial
  count, n-per-arm) was re-derived and reconciled.
- **Failure modes considered & folded in:** missing-superpowers-subject · holdout-never-runs · cost-flow-dead-end
  · Task-disallow-asymmetry · underpowered-primary-contrast · worth-loading-bar-unoperationalized
  · isolation-vs-constant-stack · mount-not-trigger-overclaim · smoke-model-vs-matrix-model · tree_sha-churn
  · truncated-trial-data-loss · allowlist-drift.

### Fold ledger

| Finding | Target | artifact:line | Confirmed |
|---|---|---|---|
| FM-1 superpowers not installed | Spike validation | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:32` | superpowers fetched from obra/superpowers, pinned 6fd4507 (v5.1.0, 14 skills), mount spike-validated |
| FM-2 holdout excluded from run | Definition of Done | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:234` | headline reframed to 100 working trials; the 25 holdout trials are explicitly not run by `fathom run` (the non_holdout filter) |
| FM-3 cost dies at ledger boundary | §11 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:210` | §11 adds a cost field to the ledger record, persists it in the CLI, and repoints the report off the never-emitted usage cost key |
| FM-4 Task-disallow hobbled humblepowers | Spike validation / Non-goals | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:48` | decision recorded: Task allowed so both plugins run as-shipped; echoed in Non-goals and the §8 allowlist |
| FM-5 underpowered primary contrast | Definition of Done | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:245` | binding verdict reset to humble-vs-bare; humble-vs-super exploratory on the separating signals; ~±0.2 Wilson at ~20/arm stated; continuous economy leaned on |
| FM-6 worth-loading bar unoperationalized | §7 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:171` | operationalized as a measurable sizing predicate (≥2 files / reproducing test / written plan); firing confirmed by the cost-probe pilot |
| FM-7 isolation vs held-constant stack | §1 / §8 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:183` | §8 lists the held-constant mounts explicitly (engineering-discipline + session-workflow), each hashed via §2; common-mode rationale in §1 |
| FM-8 mount-not-trigger overclaim | §5 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:152` | §5 renamed "mount/available"; proves mount not firing; real auto-fire deferred to the pilot |
| FM-9 smoke-model vs matrix-model | §5 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:154` | §5 asserts from the init event ("model-agnostic"); the spike confirms model-agnosticism at the init layer |
| FM-10 tree_sha churn | §2 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:134` | tree_sha defined as git write-tree of the vendored subtree at its pinned commit over tracked files only |
| FM-11 truncated trials dropped | §6 / §7 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:166` | §6/§7 set per-task limits sized for the longest allow-Task arm; the DoD recovers truncated trials from the ledger |
| FM-12 allowlist drift | §8 | `docs/specs/2026-06-14-fathom-humble-vs-super-design.md:186` | allowlist curated and justified as a deliberate, identical-across-arms deviation (still default-deny, never bypass) |

### Advisory follow-ups (non-blocking; recorded by round-2 review)

- **(a) Enforce the per-trial budget, do not just print it.** With Task allowed each spawn can fan out into
  subagents; the real guard is the adapter's per-spawn max-budget (default 5.0), not the printed per-trial
  ceiling estimate. The cost-probe pilot sets the cap — ensure the run actually plumbs it (a per-bank/per-task
  max-budget into the spawn). Highest-value pre-execution item.
- **(b) The held-constant stack is deliberately narrow** (engineering-discipline + session-workflow only); the
  stack-* verdict speaks to that stack, not a fuller one. External-validity caveat, not a bias (common-mode
  cancels).
- **(c) Holdout promotion is a small follow-up PR, not a one-liner** — it needs a CLI flag, run_matrix plumbing,
  and an ADR-0005 reclassification; correctly out of scope here.
- **(d) Broad-shell containment** is argued (default-deny, isolated network-free workspace, identical across
  arms); optionally extend the §5 default-deny probe to assert the broad-shell arm cannot touch anything outside
  the staged workspace.
- **(e) §11 is partly already done** — the adapter already computes the cost estimate; PR11 only needs the
  ledger field, CLI persistence, and the report repoint (do not re-implement the adapter parse).
