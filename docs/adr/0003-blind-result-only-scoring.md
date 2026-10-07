# ADR-0003 — Scoring is blind and result-only; trajectory and economy join after scoring

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

fathom's verdicts compare scenarios, so any leak of scenario identity into scoring
biases exactly the comparison being made. Verified prior art (Terminal-Bench)
deliberately scores only final environment state and ignores agent
commands/output; the pairwise-judging literature shows position bias is systematic
and strongest when candidates are close in quality — the marginal regime fathom must
detect. Multi-session strategies also make trajectory-aware grading incomparable
across arms (one long transcript vs many short ones).

## Decision

Verifiers receive only the final trial workspace (plus the task's fixture
reference) — no scenario metadata in argv or env. Judges receive outputs labeled
A/B with scenario identity stripped, judged in both orders, win only on
agreement, else tie. Trajectory, telemetry, and economy data join the comparison
**after** scoring, as the diagnostic layer, never inside the grade.

## Alternatives considered

- **Trajectory assertions in the grade** (promptfoo-style `trajectory:*`) —
  legitimate for debugging, but grades trajectories that differ structurally per
  strategy arm, so it cannot compare a 1-session trial with a 5-session trial.
- **Absolute rubric scores per scenario, compared arithmetically** — two noisy
  pointwise scores compare worse than one pairwise verdict, and absolute scores
  drift across judge revisions, forking longitudinal history.

## Consequences

- New invariant: **scoring inputs are scenario-blind** — verifier argv/env and
  judge prompts must contain no scenario identifiers; a review-checklist item.
- Strategy comparison (single vs multi-session) is sound by construction: the
  verifier cannot tell how many sessions produced the workspace.
- Diagnosis of *why* an arm lost happens in the report layer over ledger + run
  records, where scenario identity is fully visible.

> **Later note (2026-09-27, 0.8.0):** the decision stands; this note records how the engine
> holds it. The verifier receives the result-view path as its only argument, an environment
> reduced to system variables in which no variable names the data root (`PATH` keeps only
> its entries outside it), and an empty temporary working directory rather than the data
> root (`src/fathom/grading/verifier.py`). The agent under test is kept from the same facts,
> because what it learns it can write into the workspace the verifier scores. Trial spawns,
> the series engine and the gated strategies' gate commands receive no `FATHOM_*` variable,
> no launch-directory variable (`PWD`, `OLDPWD`) and no variable whose value names the data
> root (`without_harness_vars` and `withhold_hidden_dirs` in
> `src/fathom/adapters/claude_cli.py`, over the directories `cli.py` registers with
> `hidden_from_children` while a command runs). Each trial spawn is given its own staged
> copies of the arm's `[context]` and `[plugins]` files, so its command line names no path
> in the data root (`stage_arm_files`). A fix spawn is shown the gate commands unexpanded
> and the gate's output with the task directory and the data root masked, and whatever a
> gate command creates in the workspace is removed when it exits. The routes that stay open,
> and what a bank author does about them, are in the authoring guide
> (`skills/fathom-eval/reference/authoring.md`, section 7, and
> `skills/fathom-eval/reference/arming.md`, section 10).
