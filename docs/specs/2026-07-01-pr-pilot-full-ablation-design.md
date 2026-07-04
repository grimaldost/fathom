# Series engine COMPLETE value-side ablation — design + build spec

> Goal (operator): a COMPLETE evaluation of the series engine's value — the orchestration engine AND every
> engine-independent capability (not just the gate) — measured on the current lineup. This spec is
> executable: a continuation session builds + runs from it. Companion to
> `2026-07-01-pr-pilot-beyond-the-engine.md` (which named the gate); this generalizes to all features.

## What we are isolating (each series-engine capability -> one arm)

| Capability (engine-independent unless noted) | Arm | Isolates |
|---|---|---|
| (baseline) plain Claude | `bare` | current-model one-shot capability (the threshold floor) |
| Deterministic gate + bounded fix loop | `bare+gate` | does forced verify-and-fix beat ad-hoc self-check? |
| + Structured review (VERDICT + feedback -> fix) | `bare+gate+review` | does a review pass add over the gate? |
| Tier-scoring + prompt/series **authoring discipline** (as a context inject) | `bare+authoring` | does the decomposition/scoping brief help a bare agent? |
| Full orchestration engine (decompose -> gate -> review across a series) | `pp-series` | the whole engine stacked |
| Scope enforcement (revert out-of-scope edits) | — | **NOT cleanly measurable on self-contained tasks** — its value is whole-repo blast-radius control; flag as out-of-scope for this harness (same confound as whole-repo gate value). |

Marginal lift = each arm vs the one below it. `bare+authoring` uses fathom's existing `[context] inject`
(no new code). `pp-series` exists. The two NEW strategies to build: `bare+gate`, `bare+gate+review`.

## Metric
- **Blind acceptance pass rate** per arm (the harness-side `verify.py` oracle grades all arms identically).
- **Defect-escape rate**: fraction of runs where the agent declared done but the *visible gate* was red on
  first check (the escapes the gate prevents). Recoverable from the gate arms' first-attempt gate result.
- **Economy** (tokens / turns / sessions / $ est). Report per-arm lift at matched cost.

## The eval-design crux — visible gate vs blind oracle (do NOT conflate)
- **Visible gate** = a test command the AGENT can run (the task ships a `tests/` suite that exercises the
  feature — a *partial* correctness check). The `bare+gate` arm FORCES running it + fix-until-green; `bare`
  may or may not run it. This models the series engine's real gate (the project's own tests).
- **Blind oracle** = `verify.py`, harness-side, scenario-blind, and BROADER than the visible suite
  (property/edge cases). It grades every arm. Keeping it broader than the visible gate is what lets a gate
  arm still fail (overfitting to the visible tests) — i.e., it measures real value, not gate-gaming.
- Blindness (ADR-0003) is preserved: the agent never sees `verify.py`; the gate it runs is the task's own
  visible `tests/`.

## Build spec (fathom, free — no runs)
1. **`src/fathom/strategies/gated_session.py`** — `GatedSessionExecutor(max_fix_attempts:int)`: `runner.execute`
   the instruction; run the task's gate cmd (subprocess in workspace); if red, `runner.execute` a fix prompt
   seeded with the failing gate output; loop up to `max_fix_attempts`; return `TrialResult(runs=[all spawns],
   pin_level=PIN_STRONG, status=...)`. (`bare+gate+review` = subclass/param that adds one review `runner.execute`
   asking for a VERDICT + feedback, then a fix spawn on REQUEST_CHANGES.)
2. **`task.toml [gate] run = "..."`** (+ `taskbank.py` parse) — the agent-visible gate command (e.g.
   `python -m unittest discover -s tests -t .`). Distinct from `[verify]` (blind).
3. **Register** in `strategies/__init__.py` + the strategy->executor dispatch (find it near where
   `SingleSessionExecutor`/`SeriesExecutor` are instantiated from `scenario.strategy`), and allow the
   new strategy strings in `scenario.py` if it validates an allow-list.
4. **Tests**: `tests/test_gated_session.py` (fix-loop drives to green; caps attempts; economy aggregates all
   spawns) using a stub Runner.
5. Scenarios: `scenarios/ablation/{bare,bare-gate,bare-gate-review,bare-authoring,pp-series}.toml`
   (all model=Sonnet 5 for the mid-tier read; add an Opus set only if budget allows).

## The defect-escape bank (the CRUX + the risk)
- Needs tasks where **bare Sonnet 5 fails ~30-60%** on the blind oracle — HARDER/LONGER than `sheet`-v2
  (which it aced 5/5). Levers: much longer horizon (many interacting layers), subtle cross-module invariants,
  a broad property oracle that punishes the almost-right, and a *partial* visible `tests/` (so passing the
  gate does not equal passing the oracle).
- **Risk, stated up front:** at the current model tier it may be impractical to make bare fail on
  self-contained tasks. If, after bounded probing, bare still aces, that IS the finding: the series engine's
  engine-independent features add no measurable value for self-contained feature work at this tier; their
  value lives in whole-repo / long-horizon / governed dimensions this harness cannot isolate. Do NOT burn
  budget chasing an unfailable bare — cap the probing.

## Cost + staging
- **Build:** free.
- **Probe (feasibility):** author 1 hard task + run `bare` (n=5), iterate difficulty. Cap ~**$60** total.
  Gate: does bare land strictly in (0,1)? If not after the cap -> stop, report the "unfailable" finding.
- **Full 5-arm matrix:** only if the probe yields a discriminating bank. 5 arms x ~3 tasks x n=5, `pp-series`
  dominant -> est ~**$150-300**. Reconvene for this budget after the probe.

## Status / next
Build the strategies (free) -> probe within the cap -> report feasibility -> (if discriminating) run the
matrix on approved budget. Persisted so a fresh/compacted session resumes here.
