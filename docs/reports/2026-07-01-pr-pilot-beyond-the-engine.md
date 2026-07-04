# The series engine beyond the orchestration engine — what an in-session agent can use directly, and how to test it

- **Date:** 2026-07-01. Answers: are the series engine's non-engine capabilities (deterministic gates, scope, tiers,
  review discipline) usable WITHOUT the headless orchestration engine, could they improve an in-session
  agent, and how to test that. Companion to `2026-07-01-pr-pilot-usefulness-findings.md`.

## The distinction that matters
The series engine is two things stacked:
1. **The orchestration ENGINE** (`the series engine run`) — headless, spawns subagents in waves over a DAG, unattended,
   resumable. This is the part the v2 study found to be **overhead for self-contained feature work**.
2. **The discipline LAYER** — deterministic quality gates, scope enforcement, a bounded fix loop, structured
   review, and model-tier calibration. The engine *consumes* this layer, but **the layer is also exposed for
   direct in-session use** and does not require the engine.

The series-executor skill IS the engine-free mode: the in-session agent runs each unit as
`brief → implement → series engine gate → bounded fix → review → record`, using the CLI for deterministic
enforcement, with NO headless orchestration.

## Inventory — what the series engine provides, and how an agent uses each directly

| Capability | Engine-free? | How an in-session agent (e.g. Claude Code) uses it directly |
|---|---|---|
| **Deterministic quality gate** (`series engine gate --plan plan.toml --task <id> --on boundary`) | ✅ | Run after implementing; byte-identical pass/fail, **zero model tokens**; authoritative "done", not a self-report |
| **Scope enforcement** (scope-guard hook + scope-revert) | ✅ | Constrain edits to a declared scope; auto-revert out-of-scope autofix changes |
| **Bounded fix loop** (re-enter seeded with the failing gate, capped attempts; livelock detection) | ✅ (executor) | Fix-until-green with a hard attempt cap instead of open-ended flailing |
| **Structured review** (VERDICT contract + honest gates-evidence + one-shot) | ✅ (executor) | Spawn a review pass with the real gate evidence injected |
| **Model-tier calibration + complexity scoring** (`model-tiers`, `pr-prompt-scorer` skills) | ✅ | Score a task, pick the cheapest-adequate model, budget it |
| **Prompt / series authoring** (`pr-prompt-scorer`, `pr-series-authoring` skills) | ✅ | Decompose a goal into self-contained, well-specified prompts |
| **Worktree isolation** | ◑ | The agent can drive git worktrees directly; the executor does it per unit |
| **Cost accounting / telemetry** (`tracker`, `analyze`) | ◑ | Engine-emitted; of limited use to a single in-session agent |
| **Waves / DAG, resume / recovery, unattended run** | ✗ (engine-only) | Not applicable without the engine — this is the orchestration itself |

## The insight
The **gate is the cheap, high-value half**: deterministic, zero model tokens, and it can catch exactly what an
agent's ad-hoc self-check misses (a hidden edge case, a cross-file invariant, a property test the agent
wouldn't have run). The **orchestration is the expensive half** (~8× sessions in the v2/06-10 data) that
self-contained work doesn't need. So the highest-leverage way the series engine could help an in-session agent like
Claude Code is NOT the engine — it is **"run a deterministic gate + bounded fix before declaring done."**
That is the executor discipline, minus the orchestration.

## How to test the gate's standalone value — the sharpened value-side study
Three arms on the SAME tasks (this ISOLATES gate value from orchestration overhead — the clean measurement the
engine-vs-bare comparison could not give, per ADR-0009's confound):

| Arm | What it is |
|---|---|
| `bare` | plain Claude, single session, ad-hoc self-verification (today's baseline) |
| **`bare+gate`** | plain Claude, single session, GIVEN the deterministic gate (the task's hidden acceptance via `series engine gate`) and instructed to run it and fix until green before finishing — the discipline, no orchestration |
| `pp-series` | the full engine (orchestration + gate + review) |

**Metrics:** final correctness; **defect-escape** = fraction of runs where the agent declared "done" but the
gate failed on first check (the escapes the gate prevents); economy (tokens / turns / $). **The verdict:** if
`bare+gate` ≈ `pp-series` on correctness at a fraction of the cost, the value is in the **gate**, not the
orchestration — and the actionable recommendation is that an in-session agent should simply *use the gate*
(via the executor skill / `series engine gate`), reserving the engine for unattended batch / whole-repo / very
long-horizon work.

## What it needs (build + prerequisite)
- **A fathom `bare+gate` strategy/arm** (new harness code): a single-session spawn that, after the agent's first
  "done", runs the deterministic gate and re-prompts with the failing gate up to a bounded number of times.
  (Distinct from the existing `single-session` and `series` strategies.)
- **A defect-escape bank:** tasks where an agent's casual self-check is FALLIBLE — the hidden acceptance
  (property tests, subtle edge cases, cross-file invariants) catches what the agent would ship. This is a
  softer prerequisite than "bare fully fails": the gate can add value even on tasks bare eventually passes, by
  catching the first-pass escape. The `sheet` task's property-based verifier is a good template — but tuned so
  the agent is unlikely to run an equivalent check itself.
- **Budget:** ~$25 to author + probe defect-escape, then ~$60-120 for the 3-arm matrix (the `pp-series` arm
  dominates cost).

## Bottom line
Even where the orchestration engine is overkill, **the deterministic gate + bounded-fix discipline is
engine-free, near-zero-overhead, and the most promising way the series engine could make an in-session agent more
reliable.** Testing `bare` vs `bare+gate` vs `pp-series` is the clean, affordable experiment that would turn
that from a hypothesis into a number — and it is the value-side study, sharpened to isolate the gate.
