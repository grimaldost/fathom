# fathom feedback — polish / self-improvement audit session

- **Date:** 2026-07-05
- **Tool/version:** fathom 0.1.0 (`pyproject.toml`)
- **Source slug:** `polish-fathom-audit`
- **Context:** a full polish pass — audit the measurement-validity surfaces, reconcile specs/ADRs vs
  as-built, and **prove the run recipes by executing the free paths**. Exercised: `fathom smoke`
  (4 real-spawn runs), `fathom run --dry-run` (incl. the `--scenarios-dir` footgun), `fathom report`
  (idempotency), the ruff/pytest gates, and a blind corpus-review fan-out + a fresh-eyes review-panel.
- **Outcome:** the harness's own gates earned their keep — **`fathom smoke` caught a shipped
  regression that broke the series arm** (the genericize-paths change, merged as PR #1, left the
  engine unresolvable). Landed fixes for that (F1), a latent `dataset_version` conflation in the
  scorecard (F2), an unhandled convoy budget exit code (F6), and a CI-clustering honesty gap — plus a
  wide doc-vs-as-built reconciliation. All shipped as PR #2 (opened, not merged).

## What worked

- **`fathom smoke` is a real gate, not a vacuous one.** The engine-boundary check (group 4) went
  **7/8** the moment I ran it, on a clean `main` — it detected that the series arm spawned no `claude`.
  That is exactly the "prove isolation/wiring on real spawns" job the gate exists for; without it the
  broken series arm would have silently mis-scored every series trial as an engine error. It returns
  nonzero on failure (verified: `run_smoke` returns `0 if all_ok else 1`), so it is a true go/no-go.
- **The free validation paths proved the recipes.** `--dry-run` printed the plan + USD ceiling and the
  resume state exactly; the `--scenarios-dir` footgun reproduced concretely (correct dir → "1 planned
  (5 done)", default dir → "5 planned (1 done)" — the partial resume-match makes the *wrong-arms* run
  look like a correct resume, which is the dangerous part). `fathom report` is byte-idempotent.
- **The append-only ledger discipline held under audit.** Nothing rewrites a ledger line; the golden
  scorecard regenerates deterministically; the config_hash conditional-inclusion pattern genuinely
  preserves resume keys. The F1 fix was designed to reproduce the pre-genericize `config_hash` on the
  author's machine specifically so the series resume key would not fork.
- **The sibling calibration path modeled the right epistemics.** ADR-0007 D3 already *names* the
  pooled-CI limitation ("heuristic width, not exact coverage") and labels indeterminate cells — that
  honesty is what the headline scorecard was missing, and it gave the review-panel a clear precedent.

## Friction

- **[MED] phase: report generation (F2, latent).** The scorecard keyed trials by
  `(scenario, task, repeat)` with no `dataset_version`, so a dv bump silently conflated task versions
  under one arm. This was already reported in the 2026-07-01 feedback (#1) and had **not** been fixed;
  it fired again here on a synthetic ledger (old-version passes leaking into a hardened-version row →
  a conflated 50%). Fixed this session (scope to current dv + warn).
- **[MED] phase: series contract sync (F6).** convoy added a fifth exit code (`EXIT_BUDGET=4` /
  `outcome="budget"`, documented in convoy `docs/design/02-formats.md`) but fathom's engine-agnostic
  contract and `_classify` still enumerated only 0/1/2/3. A budget-cap halt fell through to an opaque
  `"engine exit 4"`. The producer conformed; the *consumer + the fathom-owned contract* lagged.
- **[LOW] phase: measurement honesty (F3).** The headline pooled Wilson CI carried no clustering
  caveat, unlike its own sibling (calibration). Not a code bug — a disclosure gap on an interval
  already hedged "directional, not final". Addressed via review-panel (added K + a concrete caveat).
- **[LOW] my own mis-inference.** I first modeled the F2 defect as a *double-count* and wrote a test
  asserting N=4; rendering the actual fixture showed the real mechanism is *last-write-wins version
  mixing* (N=2, 50%). Corrected by observing the source (data-engineering-discipline axiom 2) rather
  than trusting my trace — the same axiom later corrected a workflow verifier's overstatement (below).

## Misses (and the phase that should have caught them)

- **The F1 series-arm break shipped green in PR #1.** The genericize change passed `ruff`/`pytest`
  (unit tests stub the engine, so no test exercises the real invocation path) and was merged. **Only a
  real-spawn `fathom smoke` catches it** — and smoke is not in any automated gate, so the regression
  reached `main`. *Proposed:* wire `fathom smoke` (or at least a non-spawning invocation-path unit
  test — added: `TestRepoInvocationCmd`) into pre-merge so a broken series arm cannot land green again.
- **The `infra_error` phantom field.** `report.py`/`calibration.py` filter trials on an `infra_error`
  key the producer never writes (infra trials halt with no ledger line; the real gate is
  `status=="completed"`). Two blind reviewers flagged it independently. Harmless today, but it reads
  as a live contract and the "Infra Errors" column is always 0. Deferred (removing it ripples into the
  scorecard format + golden) — tracked here for a focused follow-up.
- **A blind-workflow verifier overstated F6** ("recorded as a scored red"). Tracing the source showed
  an ERRORED trial is *excluded* from the pass rate (`status=="completed"` gate), so the real harm was
  narrower (opaque detail + wasted verifier run + spec gap). The adversarial-verify stage caught the
  finding but not its own severity error — the human/main-loop source read remained load-bearing.

## Vacuous gates

None. `fathom smoke`, `ruff`, and `pytest` each did real work and each *could* (and did) fail. The
smoke engine-boundary check in particular failed loudly on a real regression.

## Proposed promotions / changes

1. **[HIGH]** Add a pre-merge gate that exercises the series invocation path — either `fathom smoke`
   in CI or, at minimum, the new `TestRepoInvocationCmd` unit assertion — so a broken series arm
   cannot merge green (root cause of F1 reaching `main`). Home: CI config / `tests/`.
2. **[MED]** Resolve the `infra_error` phantom field: either persist an infra-errored trial line
   before the clean stop (making the column + filters real) or remove the dead guards and the
   always-0 "Infra Errors" column, relying on `status=="completed"` (the real invariant). Home:
   `report.py`, `calibration.py`, fixtures.
3. **[LOW]** A deliberate way to render a *chosen historical* `dataset_version` (analogous to
   `--include-holdout`), since the default now scopes to current — so the append-only record stays
   inspectable, not just archived (review-panel suggestion). Home: `cli.py report` / `report.render`.
4. **[LOW]** Consider a design-effect-inflated Wilson (divide effective N by `1+(r-1)ρ`) as a future
   mechanical guard on the pooled CI, if the advisory K + caveat proves insufficient (review-panel
   follow-up, explicitly a later step). Home: `report.py`.

## Cost (economy — subscription auth, real ~$0; token figures measured, USD is a list-price estimate)

| activity | agents/spawns | tokens (measured) | wall-clock | est. USD (list) |
|---|---|---|---|---|
| `fathom smoke` × 4 real-spawn runs | ~8 haiku spawns each | negligible (haiku, ≤2 turns) | ~4 × ~90 s | <$0.20 |
| blind corpus-review fan-out (Workflow) | 25 subagents | 1,450,364 | 345 s | ~$12 |
| estimator review-panel (Workflow) | 4 subagents | 237,145 | 136 s | ~$2 |
| `--dry-run` × 2, `fathom report` × 3 | 0 (no spawns) | 0 | seconds | $0 |
| **total tool-driven** | **~29 subagents + smoke** | **~1.69M** | **~11 min** | **~$14 (list); real ~$0** |

All authoring + audit + validation gates were free of paid matrix spend; the only real spawns were the
smoke haiku probes. No paid matrix was run this session (none was needed for a polish pass).
