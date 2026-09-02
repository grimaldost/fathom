# Design — the gate as a hook, per-project gates, and the closed-loop model × oracle crossing on real PRs

- **Date:** 2026-09-02. **Status:** draft, for the operator's three decisions at the end.
  Nothing here starts before iteration 1 (bank `multiagent-composition-v2`, main matrix
  in flight) reads out and is blind-reviewed.
- **Extends:** `2026-07-14-tier-separating-bank-design.md` Part C (the model × oracle-quality
  crossing, authored open-loop and never run) — this design closes the loop the earlier one
  said it could not: "with no fix loop it cannot show that the weak model, confronted with
  the sharper oracle, would then succeed." Convoy's gate plus a repair step is that loop.
- **Evidence this rests on (iteration 1, so far):** with rule-explicit briefs no gate has
  anything to catch (v1: 24/24 at ceiling); with lossy briefs multiagent alone fails the
  held-out oracle 0/8 at both tiers while convoy's gate arms read 14/15, placebo 2/6; the
  treatment's extra cost is orchestrator turns and context (placebo costs the same as the
  gate arm in turns/tokens), not the deterministic gate, which costs $0 in model.

## Part 1 — convoy 0.12.0: the gate the orchestrator never has to think about

**1a. `convoy hook` — a `PostToolUse` command hook on the `Agent` tool.** Reads the hook
JSON on stdin; if `tool_name` is not `Agent` (alias `Task`, pre-2.1.63) it exits 0. It
locates the project's gate spec (below); if none exists it exits 0 silently — **the
presence of a spec is the per-project switch**, so shipping the hook in the plugin arms
nothing until a project opts in. It runs the gate through `gate_service` (same fold as
`convoy gate`). Green: exit 0, no stdout, no JSON — nothing enters the orchestrator's
context. Red: exit 2 with the compact `repair_brief` on stderr (documented as "shown to
Claude; the tool already ran"), which is the orchestrator's cue to dispatch a fix
subagent; every re-dispatch re-fires the hook, so the loop closes without the orchestrator
ever running or reading a gate itself. Phase scoping: the hook reads an optional
`[convoy-phase: <tag>]` marker in `tool_input.prompt` (the subagent's brief); absent, the
whole gate runs. Attestation: the hook appends one JSON line per firing to
`.convoy/hook.log` (gitignored by the scaffold) — verdict, `convoy_version`, phases,
checks, cost of the commands' wall-clock — so an experiment counts firings from the log,
not from transcripts.

**1b. Plugin-shipped hook.** `hooks/hooks.json` with `PostToolUse`, matcher `Agent|Task`,
`uv run --project "${CLAUDE_PLUGIN_ROOT}" convoy hook`, timeout raised to the gate's
`timeout_seconds` + margin. Installing the plugin arms it; a project's own
`.claude/settings.json` hook coexists (documented: all matching hooks run).

**1c. Per-project gate spec.** `convoy gate` and `convoy hook` with no series argument
look for `$CLAUDE_PROJECT_DIR/.convoy/gate.toml` (then `./.convoy/gate.toml` from cwd) —
the gate-only file shape that 0.10.0 already accepts. `convoy gate --init` scaffolds it
from toolchain detection — Python: `uv lock --check`, ruff check, ruff format --check, the
type checker present, pytest; Node: the lint/typecheck/test scripts in package.json; else a
commented skeleton — as **blocking, non-independent** checks: the project's own suite,
which is the default gate and is also exactly what the implementer can satisfy by
self-report. The scaffold's header says so, and names the next step.

**1d. Independent checks per project — judge before defendant.** An independent check
needs an asset the implementer cannot reach, and in-tree is reachable by construction
(fail-closed isolation refuses it). The convention: `CONVOY_ORACLES` (default
`~/.convoy/oracles/<repo-slug>/`) holds the project's held-out oracles; a check declares
`independent = true`, `asset = "${CONVOY_ORACLES}/<file>"` (the loader expands the
variable), and `convoy gate --init --independent <name>` scaffolds one there with the
`repair_hint` field prompted. The doctrine sentence that goes with it, in
`docs/authoring-series.md`: **the spec author writes the independent checks before
dispatching any implementer** — the judge is appointed before the defendant. Where a
project has none, the hook still runs the default gate, and the manual says plainly that
this catches regressions, not the class the held-out oracle catches.

**1e. Compact envelope.** `convoy gate --brief` (and `convoy_gate(brief=true)`) return
`{ok, outcome, repair_brief, convoy_version}` only — for callers that must read the result
in a model turn, the hook path being the one that avoids the turn altogether.

Ships as 0.12.0 via convoy's own process (TDD, blind review, changelog gate). Consumer-
affecting: a new command, a hook file, a spec-discovery rule, `--brief`.

## Part 2 — the mechanism arm on the existing bank (cheap, before the hard bank)

Before authoring anything expensive, add two arms to `multiagent-composition-v2` —
`hook-haiku`, `hook-sonnet`: control's brief byte-for-byte (the orchestrator is told
nothing about gates), the plugin hook armed, the project gate spec materialized by the
driver into the workspace's `.convoy/gate.toml` with the same two independent probes. n =
16 to match. Pre-registered prediction: `held_out_clean` ≈ `perpr` (the same oracle, the
same repair information), at **control's turn count and tokens** (the placebo-shaped
overhead disappears) — the cost claim of Part 1 tested against the cells that already
exist. ~$40 per tier-set.

## Part 3 — bank `treasuryutils-prs`: real PR-sized tasks, held-out oracles from history

- **Source:** `treasuryutils-dev` — 1,042 Python files, 457 test files, ruff + uv, 435
  merge commits in 90 days, PR numbers in the merge subjects. Proprietary: the bank lives
  **outside the fathom repo** (a private tasks dir passed with `--tasks-dir`); only
  `record.yaml`, the scenario TOMLs and the report enter fathom.
- **Task construction (mechanical, agent-assisted, then screened):** for each merged PR
  with test changes and 40–900 changed lines — fixture = the repo at the merge's first
  parent; instruction = the PR's title and body plus a brief rewritten in the task-statement
  register (what to build, not how); **held-out oracle** = the tests the PR added or
  changed, withheld from the implementer, run against its workspace; visible gate = the
  repo's suite at the parent commit; regression criterion = the parent's suite stays green.
- **Admission screen (Part B of the 2026-07-14 design):** a task is admitted only if the
  rubric tier's implementer fails the held-out oracle at least once in a 3-trial screen
  and the reference PR passes it 3/3 — "gap, not flaky". Target 10–12 admitted tasks,
  spread by rubric tier (some mid, some strong).
- **Tiers from choosing-models, as practiced:** each task is scored with the rubric
  (score, tier, model, effort) and the pin is recorded in the task's `task.toml` under a
  `[routing]` block — the prediction the experiment reconciles.

## Part 4 — the experiment: closed-loop model × oracle crossing

**Factors.** Implementer tier {**rubric** (choosing-models' pick), **down** (one tier
below it)} × gate {**none** — the orchestrator verifies with the visible suite and
self-reports; **hook** — convoy's plugin hook with the project's independent checks}.
Orchestrator fixed (Sonnet 5, effort high). One implementer subagent per task plus fix
subagents on red — the operator's actual dispatch shape (an orchestrator session
dispatching implementers), with single-PR tasks; multi-PR chains are a later factor.

**Endpoints.** Primary `held_out_clean` (the withheld tests pass and the parent suite
stays green); cost per trial and per *correct* trial; wall-clock; mechanism (hook firings,
first-red rate, fix dispatches, from `.convoy/hook.log`).

**Pre-registered contrasts (Holm over the family, one-sided):**
1. **down + hook vs rubric + none** — the licensing claim: a cheaper model with convoy's
   gate is at least as good as choosing-models' own pick without it. This is the contrast
   that recalibrates the oracle-coverage discount.
2. hook vs none at the rubric tier; 3. hook vs none at the down tier (the interaction:
   the weak tier's slope should be the steeper one — the 2026-07-14 hypothesis, now
   closed-loop).
4. Cost per correct task, down + hook vs rubric + none (the efficiency claim).

**Decision rule for choosing-models** (its `models.toml` ships the oracle-coverage
discount as a labeled hypothesis for exactly this): contrast 1 supported at α = 0.05 after
Holm AND contrast 4 favorable → keep the discount and quantify it (the observed down-tier
pass rate under the hook becomes the calibration note); contrast 1 null with adequate
power → **retire** the discount; contrast 3 null → the interaction is absent and the
discount is retired regardless of 1.

**Exploratory cells (declared now, outside the Holm family):** (e1) down + hook +
*convoy-aware brief* — a shorter implementer brief that states what to build and delegates
verification ("a gate you cannot see will check the contract; do not write your own
tests for it"); (e2) down + hook at **effort medium**. These test the operator's
hypothesis that with convoy holding verification, the implementer's prompt can be
simpler and its effort lower. Reported as signals, never as findings.

**n and budget.** Pilot: 4 cells × admitted tasks × 1 repeat, to estimate rates and cost;
main n from the pilot's contrast-1 gap by the exact power calculation, run as interleaved
passes. Real-repo Sonnet trials are expected at $3–8; four cells × 10 tasks × 3 repeats ≈
120 trials could exceed the $400 iteration cap — the pilot prices it, and the operator
decides between fewer repeats, fewer tasks, or a larger cap.

**Threats, named now:** the held-out oracle is the PR author's tests — a *human* oracle
whose coverage varies by PR (recorded per task: lines/branches the withheld tests touch);
model_version_drift across a multi-day matrix; contamination (the models may have seen
the repo's public dependencies, not this private code); the down tier's fix loop may
converge by trial-and-error on the visible suite rather than by understanding — which the
held-out oracle is there to catch, and which the cost-per-correct endpoint prices.

## Sequencing

1. Iteration 1 closes: v2 main matrix → `record.yaml` results → `validate.py` → derived
   `report.md` → two blind reviewers → feedback reports.
2. Convoy 0.12.0 (Part 1) — build, review, release. Then Part 2 on bank v2 (~$80).
3. Bank `treasuryutils-prs` authoring and screening (Part 3), private tasks dir.
4. Pre-registration → pilot → main matrix → derived report → blind review →
   choosing-models recalibration through its own refresh process.

## Decisions taken — 2026-09-02

1. Data boundary: **confirmed** — the bank is a private local tasks directory, never
   committed to fathom; only the record, the scenarios and the derived report enter.
2. Iteration-2 budget: **$600 cap**, the pilot prices the main matrix, both pre-registered
   before the first paid trial of each stage.
3. Task shape: **single-PR tasks** now; multi-PR chains as a later factor.

## The operator's three decisions (as put)

1. **Data boundary.** treasuryutils-dev's code will reach the model API in every trial —
   the same path the operator's daily Claude Code use already takes on that repo. Confirm
   that this is acceptable for a measurement run, and that the bank stays private (never
   committed to fathom).
2. **Budget for iteration 2.** Real-repo trials cost 2–4× the toy's. The pilot prices the
   matrix; if it lands above $400, the choice is fewer repeats (n = 2), fewer tasks (8), or
   a higher cap for this iteration.
3. **Task shape.** Single-PR tasks (orchestrator + one implementer + fix loop) are cheaper
   and match the operator's dispatch practice; multi-PR chains reintroduce integration
   effects and cost. Default: single-PR now, chains as a later factor.
