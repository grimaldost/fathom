# Run notes — skill-pyeng-v1 first matrix (python-engineering effectiveness)

**Date:** 2026-06-13 · **Bank:** skill-pyeng-v1 (dataset_version 1; task `modernize-timeflow`)
**Matrix:** 3 scenarios × 1 task × 3 repeats = 9 trials · single-session · model `claude-opus-4-8` effort `high`
**Question:** does force-loading `engineering-discipline:python-engineering` make an agent modernize a
legacy flat-layout project to the skill's *own* standard (its bundled `doctor.py` audit), holding
correctness, and at what cost — vs a bare agent and a generic "write good Python" nudge?

## Run 1 — INVALID (max_turns truncation)

First execution: 8/9 trials `errored`, all at `num_turns≈31`, all well under the 600 s timeout.
Root cause: `task.limits.max_turns = 60` was **dead config** — nothing plumbed it to the adapter,
which hardcapped at its default 30. Confirmed by a diagnostic spawn (`--max-turns 5` → error at
`num_turns=6`). Even truncated, the verifier scored partial compliance and the signal was already
visible (pyeng-skill 5/5 ×3 vs bare/generic ~2.3/5). Archived append-only at
`ledger/archive/skill-pyeng-v1.run1-invalid-maxturns-truncated.jsonl`. Fix `77465bc`: thread an
optional `max_turns` through `Runner.execute`; the single-session executor passes
`task.limits.max_turns`; budget bumped to 80.

## Run 2 — VALID

Re-ran fresh at the 80-turn budget. 8/9 completed (1 `bare` trial errored — the un-guided arm is
high-variance and one rollout flailed past the budget; it had still reached 3/5).

### Scorecard — per-criterion compliance (the discriminating view)

| Criterion | bare | generic-nudge | pyeng-skill |
|---|---|---|---|
| behavior_preserved | 100% (2/2) | 100% (3/3) | 100% (3/3) |
| src-layout | 100% | 100% | 100% |
| dependency-groups | 100% | 100% | 100% |
| pip-audit | 50% (1/2) | 33% (1/3) | **100% (3/3)** |
| ruff-single-quote | **0%** | **0%** | **100%** |
| uv (build backend) | **0%** | **0%** | **100%** |
| **Full 5/5 compliance** | **0/2** | **0/3** | **3/3** |

### Verdict (directional)

**Loading `python-engineering` drove the agent to full (5/5) compliance every time; bare and a
generic quality nudge plateaued at 2–3/5 even when they ran to completion** (so it is not merely
"the skill is faster" — the others did not catch up given the turn budget). `behavior_preserved` was
True for all 9 — no arm broke the public functions.

The per-criterion table **localizes where the skill adds value**:
- **Common knowledge — no skill needed:** every arm did `src-layout` and PEP 735
  `dependency-groups` (widely-known modern practice).
- **The skill's opinionated, specific conventions — skill-only:** `uv` build backend and ruff
  single-quote config were done by the skill arm **100%** and by bare/generic **0%**. `pip-audit`
  (security): skill 100%, others 33–50%.
- **`generic-nudge ≈ bare`** on every criterion — so the lift is `python-engineering`'s *specific
  content*, not a generic instruction to be careful.

### Economy

| Scenario | Tokens | Turns | Wall-clock (s) | Sessions/trial | Est. USD |
|---|---|---|---|---|---|
| bare | 26,830 | 44 | 329 | 1.0 | (0 — D2) |
| generic-nudge | 69,718 | 111 | 888 | 1.0 | (0 — D2) |
| pyeng-skill | 76,681 | 111 | 1,027 | 1.0 | (0 — D2) |

Per trial: bare ~22 turns / 13k tokens; generic and skill ~37 turns / 23–26k tokens. **The generic
nudge spends the same effort as the skill (~37 turns) but does not convert it to compliance** — it
"tries harder" without the specific knowledge. The skill's marginal cost over bare (~2× tokens) buys
an outcome bare cannot reach at any observed turn count. Injecting the ~4k-token skill body is a
small part of the delta; most is the agent doing more real work.

## Defects / findings (the dogfooding payoff)

- **D-maxturns (fixed, `77465bc`):** `task.limits.max_turns` was never plumbed to the adapter →
  every spawn capped at 30 → 8/9 run-1 trials truncated. Regression-tested.
- **D2 (open, carried from the series-engine bank):** `cost_usd_est = 0` for adapter runs — the subscription
  stream's cost field isn't surfaced. Tokens/turns/wall-clock are the primary currency (C1), so the
  verdict stands, but fix before any USD claim.
- **[reporting] errored trials excluded from the per-criterion table** — correct in general, but a
  harness-limit truncation (max-turns/timeout) hides real partial-compliance data; run 1's signal
  was only visible by reading the ledger directly. Consider a distinct status for budget-exhaustion
  vs task-error.
- **[verifier design lesson, fixed in `2750fe6`]** the behavior check must import the candidate as a
  *package*, or a valid src-layout refactor with a relative import is graded a behavior failure —
  which would bias against the very treatment the bank rewards.

## §-done-criteria status

1. Resumable matrix — demonstrated (run 1 → archive → run 2 fresh). ✓
2. Smoke before paid runs — **6/6**, including the new K7 injection-armed check
   (`canary_present=True` on a real spawn). ✓
3. Stdlib-runnable core tests — 308 passing. ✓
4. Full paid run + scorecard with per-criterion verdict + economy. ✓
5. Ledger committed; run 1 archived without clobbering. ✓ (this commit)

## Experiment-design note (v2)

A discriminating bank by construction: the legacy fixture starts at 0/5, and the criteria span
common-knowledge (everyone passes) and skill-specific (only the skill passes) — which is *why* the
result localizes the skill's value rather than giving one blurred number. The quality axis (the
dark-shipped judge: is the architecture genuinely better beyond doctor's mechanical checks) remains
Phase 2.
