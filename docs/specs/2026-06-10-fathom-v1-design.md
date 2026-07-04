# fathom v1 — design spec

**Date:** 2026-06-10
**Status:** Approved design, pre-DoR
**Evidence base:** `craft-collection/docs/research/2026-06-10-tool-effectiveness-eval-prior-art.md`
(deep research, 23 sources, 25 claims adversarially verified). Methodology anchors cited inline as
[R§n] refer to that report's numbered findings.

## 1. Purpose

fathom measures whether an AI coding tool is worth using. It scores **task results blind to
scenario**, compares scenarios (with tool / with alternative / bare agent / different execution
strategies), and joins the comparison with per-run economy data (tokens, turns, wall-clock,
sessions, estimated USD) into longitudinal verdicts: *worth using*, *which direction to improve*,
*did the new version regress*.

It is the quantitative arm of a three-arm system: fathom (lab), Claude Code OTel telemetry (field,
deferred to v2), and the existing tool-feedback/feedback-triage loop (qualitative).

### Why a dedicated repo

The harness serves three tool repos (craft-collection, keel, convoy); the longitudinal ledger
must outlive any one tool's branch state; and the prior harness lived inside one of its own test
subjects (craft-collection), which also exposed it to known concurrent-session/shared-worktree
hazards. (Architectural inference — repo-organization prior art did not survive verification
[report: open question 5].)

## 2. Goals and non-goals

### v1 goals

1. The **spine**: vendor-abstract runner, trial/run ledger with idempotent resume, scenario
   matrix with a named bare-control arm, deterministic-verifier-first grading with swap-order
   pairwise behind it, scorecard report.
2. One real question answered end-to-end: **single long session vs the series engine's multi-session series
   vs bare Claude Code**, on a 3–5 task bank (the series-engine bank).

### Non-goals (deferred, interface-ready)

- OTel stamping + local collector + telemetry join (v2; v1 economy comes from `claude -p`
  stream-json result events).
- Trigger-axis (recall/specificity) migration — stays in craft-collection `evals/` until fathom
  reaches parity (v2+).
- keel task bank; non-Claude runner adapters; Docker-isolated workspaces; retiring
  craft-collection `evals/`.

## 3. Constraints

| # | Constraint | Consequence |
|---|---|---|
| C1 | Start on Claude subscription auth; never couple to it | `Runner` protocol; `claude-cli` adapter first; judge calls use the same abstraction; USD is an adapter estimate — tokens/turns/wall-clock are primary economy currency |
| C2 | Scenarios are execution strategies, not flag sets | `StrategyExecutor` protocol; **trial** (scored attempt, 1..N runs) vs **run** (one invocation) two-level ledger; verifiers see only the final workspace |
| C3 | Windows host, no Docker in v1 | Workspace = temp dir copied from fixtures (proven pattern); container isolation can slot in later without task-format change |
| C4 | Personal cost scale | Per-spawn `--max-budget-usd` + `--max-turns`; upfront spawn-count and cost-ceiling print; `--dry-run`/`--limit` on every entry point; expect $20–40 per full v1 run (series arm is multi-session) |
| C5 | Blindness invariant | `verify.py` receives only the final workspace (+ fixture reference); judges receive outputs labeled A/B with scenario metadata stripped; trajectory/economy join AFTER scoring, diagnostic only [R§1] |
| C6 | Sealed holdouts | Bank manifest marks holdout tasks; holdout results reported separately; a spent holdout is dev data (established practice) |

## 4. Architecture

### 4.1 Repository layout

```
fathom/
  pyproject.toml            # uv, src-layout, ruff, pytest
  src/fathom/
    cli.py                  # fathom run | report | smoke (argparse)
    taskbank.py             # bank manifest + task loading, stable IDs, holdout split
    scenario.py             # scenario parsing, pin resolution, config hashing
    ledger.py               # append-only JSONL, resume keys, integrity-tolerant reads
    adapters/
      base.py               # Runner protocol + RunRecord
      claude_cli.py         # vendored from craft-collection evals/harness/claude_runner.py
    strategies/
      base.py               # StrategyExecutor protocol + TrialResult
      single_session.py     # 1 run per trial
      series.py             # N runs per trial via the series engine
    grading/
      verifier.py           # run task verify.py against final workspace
      judge.py              # swap-order pairwise + tie (ported from evals/harness/judge.py)
    report.py               # scorecard.md from ledger; Wilson CIs (port stats.py)
  tasks/<bank>/             # bank.toml + <task-id>/{task.toml, fixtures/, verify.py[, rubric.json]}
  scenarios/*.toml
  ledger/*.jsonl            # committed: the longitudinal record
  report/                   # generated, gitignored
  tests/                    # stdlib-runnable unit tests + smoke gate
  docs/specs/, docs/feedback/
```

Dependency policy: the spawning/ledger core imports stdlib only (unit tests run anywhere); uv
manages dev tooling. `typing.Protocol` at the seams.

### 4.2 Task bank format (Harbor-shaped [R§2], minus Docker)

`tasks/<bank>/bank.toml`:

```toml
[bank]
name = "series-engine-v1"
dataset_version = "1"        # bumped on ANY task/fixture/verifier change
holdout = ["task-id", ...]
```

`tasks/<bank>/<task-id>/task.toml`:

```toml
[task]
id = "cfg-loader"            # stable; never renumbered (resume keys depend on it)
instruction = """..."""      # what the agent is asked to do
[task.limits]
trial_timeout_s = 1800
[task.verify]
entry = "verify.py"          # exit code + per-criterion JSON to stdout
```

`fixtures/` seeds the trial workspace. `verify.py` runs in the harness env (not the agent's),
receives the final workspace path as argv, and must not read scenario metadata (C5). Optional
`rubric.json` declares judge axes for qualities no verifier can express; tightly specified binary
criteria only [R§9].

### 4.3 Scenarios

`scenarios/<id>.toml` — declarative; resolution pins everything and computes `config_hash`:

> **⚠ As-built note (2026-06-14):** the block below is the *design-time* sketch and drifted in
> implementation. The real schema is **flat top-level** (no `[scenario]` table): `name` (not `id`),
> `adapter`, `model`, `strategy`, `effort`; `[tools] source = "none" | "repo"` with
> `repo`/`allowed`/`disallowed`; an optional `[context] inject = "<file>"` (treatment arm); and
> `[limits] trial_timeout_s`. Source of truth: `src/fathom/scenario.py` and the real files in `scenarios/`;
> see `CLAUDE.md` → "Authoring banks / scenarios".

```toml
[scenario]
id = "series"
adapter = "claude-cli"
model = "sonnet"             # resolved to exact model id at run time, recorded
strategy = "series"
[scenario.tools]
source = "repo"              # none | plugin-dir | repo
path = "/path/to/pr-pilot-main"
# resolved git SHA recorded per trial as tool_git_sha
[scenario.limits]
max_budget_usd_per_run = 2.0
max_turns = 50
```

v1 ships three: `bare` (clean config, no tools — the control [R§5]), `single-long-session`
(clean config, one spawn, full instruction), `series` (engine-driven N spawns).

### 4.4 Execution abstractions (C1, C2)

```python
class Runner(Protocol):
    def execute(self, prompt: str, workspace: Path, scenario: ResolvedScenario) -> RunRecord: ...

class StrategyExecutor(Protocol):
    def run_trial(self, task: Task, workspace: Path,
                  scenario: ResolvedScenario, runner: Runner) -> TrialResult: ...
```

`claude_cli.Runner` vendors the proven core: temp `CLAUDE_CONFIG_DIR` containing only the copied
credential, headless default-deny permissions (never `bypassPermissions`), explicit allow/disallow
lists, `--output-format stream-json` parsing with partial-stream tolerance, retry with cap.
`RunRecord` carries usage (input/output/cache tokens), `num_turns`, duration, estimated USD, exit
status, CLI version.

The judge is a `Runner` call too — same adapter, no tools, strict-JSON prompt.

### 4.5 Ledger (Inspect-shaped [R§3])

Append-only JSONL, one file per question/bank under `ledger/`, committed to git. Three record
kinds:

```jsonl
{"kind":"trial","trial_id":…,"bank":…,"dataset_version":…,"task_id":…,"scenario_id":…,
 "config_hash":…,"tool_git_sha":…,"cli_version":…,"repeat":0,"status":"complete|errored",
 "verifier":{"pass":true,"criteria":{…}},"started_at":…,"ended_at":…}
{"kind":"run","run_id":…,"trial_id":…,"seq":1,"model_resolved":…,"usage":{…},"num_turns":…,
 "duration_s":…,"cost_usd_est":…,"exit":"ok|timeout|error"}
{"kind":"grading","pair":[trial_id_a,trial_id_b],"axis":…,"order_ab":…,"order_ba":…,
 "verdict":"win|tie|loss","judge_model_resolved":…,"judge_config_hash":…}
```

**Resume key:** `(bank, dataset_version, task_id, config_hash, repeat)`. A re-run skips completed
tuples; a fully complete matrix is a no-op; an `errored` trial is retried up to a cap. Reports are
regenerated from the ledger, never merged read-modify-write — this removes the old harness's
clobber/overwrite failure modes by construction. Reads tolerate and warn on malformed lines.
Version pins (`dataset_version`, `config_hash`, `tool_git_sha`, `cli_version`,
`judge_config_hash`) are recorded per record so longitudinal history never silently forks [R§11].

### 4.6 Grading flow

1. **Deterministic verifier first** [R§1, R§9] — runs on every completed trial, blind (C5).
2. **Pairwise judge** only for declared rubric axes: each (treatment trial, bare-anchor trial)
   pair judged in both orders; win only when both orders agree, else tie [R§7]. Trials pair by
   matching repeat index (repeat-k vs repeat-k), so judge volume scales linearly with repeats.
   At 3 scenarios this is ≤6 judge calls per task per repeat including swaps [R§6]. Judge tier per task family, validated
   on our own tasks before trusting [R§8]; gold-set κ on fuzzy rubrics is weak evidence [R§9].
3. Repeats: default 2–3 per (task, scenario); a task failing ~half its runs across scenarios is
   flagged "ambiguous — fix the task" rather than retried away [R§4]. Repeat budget is calibrated
   empirically (open item), since no field standard exists [refuted claims].

### 4.7 Report

`fathom report <bank>` renders `report/scorecard-<bank>.md` from the ledger: per-scenario verifier
pass-rate with Wilson 95% CI, pairwise win/tie/loss vs bare per axis, economy table (tokens,
turns, wall-clock, sessions/trial, USD-est), holdout results separated, and one verdict line per
scenario. Directional language until judge validation exists (inherited stance).

## 5. v1 question definition

**Bank (the series-engine bank):** 3–5 realistic Python tasks at the coordination threshold — multi-file
feature/fix work where decomposition into a series plausibly helps (the regime the series engine claims).
Each task: fixture repo skeleton, instruction, deterministic verifier (tests pass, files/behavior
expected), trial timeout.

**Arms:** `bare` · `single-long-session` · `series`.

**v1 is done when:**

1. `fathom run <the series-engine bank>` executes the full matrix, resumably — interrupting and re-invoking
   re-spawns nothing already complete (demonstrated, not asserted).
2. `fathom smoke` passes the ported isolation assertions on real spawns (clean config
   authenticated; allowlist enforced; stream parse detects activity) before any paid run.
3. Unit tests for ledger resume, config hashing, scenario resolution, and verifier protocol run
   stdlib-only and pass.
4. One full paid run completes and `fathom report` renders a scorecard with a defensible verdict
   on the question, including per-trial session counts and economy.
5. The ledger from that run is committed and a second partial run appends to it without
   clobbering history.

## 6. Error handling

- Spawn failure → retry with cap (vendored behavior); timeout → partial stream still parsed;
  trial marked `errored` only after retries exhausted.
- Verifier crash or non-JSON output → trial `errored` (never silently scored fail) and surfaced
  in the report's error column.
- Series-arm engine failure mid-trial → trial `errored` with runs-so-far recorded (economy data
  retained for diagnosis).
- Budget ceiling reached mid-matrix → clean stop; ledger state is the checkpoint; resume
  continues.

## 7. Testing

- Pure-logic unit tests (stdlib-runnable, no spawns, no cost): ledger append/read/resume-key
  logic incl. malformed-line tolerance; config hashing stability; scenario resolution and pin
  recording; verifier-protocol parsing; report aggregation incl. Wilson CI (port existing tests).
- `fathom smoke`: few real spawns asserting the three load-bearing isolation properties (gate
  before any paid matrix).
- The v1 paid run itself doubles as the acceptance test for success criteria 1, 4, 5.

## 8. Open items (to resolve before/at DoR)

1. **Series engine invocation** for `series.py`: exact entry point, how the engine's
   own spawns are authenticated (subscription?), and where per-run usage lands (engine cost
   table vs wrapping each spawn). Requires a look inside the series engine repo.
2. **Repeat budget**: start at 2–3; calibrate from observed variance on the v1 bank.
3. **Judge tier** for code-quality axes (if any rubric axis survives task design — prefer
   verifier-only for v1 if possible, which sidesteps judge validation entirely).
4. **Billing watch**: verify how subscription programmatic `claude -p` use is budgeted/billed
   before scaling run counts (unverified secondary report in the research source pool).

## 9. Decision log

| Decision | Choice | Alternatives rejected |
|---|---|---|
| Relation to existing harness | Extract-and-generalize: vendor `claude_runner.py` core, refactor behind `Runner` | Import evals/ as dependency (couples to a test subject); greenfield rewrite (discards debugged isolation) |
| v1 scope | Spine + series-engine question | Infrastructure-first (no consuming question); breadth-first banks (spreads hardest work thin) |
| Name / location | `fathom`, `/path/to/fathom` | gauge, proving-ground, benchrest |
| Frameworks | Adopt patterns, not runtimes [report recommendation] | Running on Inspect/promptfoo (API-key-centric; subscription `claude -p` is both SUT and judge transport) |
| Governance | keel apply-method binds fathom; build runs as a governed series | Generic plan-only flow |
