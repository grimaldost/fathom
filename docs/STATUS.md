# fathom — status & next steps

*The index of what's been run, what's open, and what's next. Per-run detail lives in the run notes
under `docs/feedback/*-first-matrix.md`; this file points at them. Update it when a run or a defect
changes state.*

## Build state

v1 spine complete — vendor-abstract runner, two-level (trial/run) append-only ledger with idempotent
resume, scenario matrix with a named bare control, deterministic-verifier-first grading (swap-order
pairwise judge behind it), scorecard report — plus the skill-effectiveness extension: per-scenario
`[context] inject` system-prompt injection and the K7 injection smoke check, and `[plugins] mount`
whole-plugin arming via `--plugin-dir`. **486** stdlib-runnable tests; `fathom smoke` 8/8. Built with the
keel/convoy governed-series method. Banks `humble-vs-super-v3` (correctness-trap) and `-v4` (non-local
root-cause) add the harder instruments + their `verify.py` discrimination tests (see Analyses run).

## Analyses run

| Bank | Question | Verdict | Run notes |
|---|---|---|---|
| the series-engine bank | single long session vs the series engine's multi-session series vs bare, on 3 dev tasks | the series engine's pipeline gave **no quality gain** over a bare single session at ~4.6× tokens and 8 sessions/trial — the tasks sat below the coordination threshold (ceiling effect: bare 6/6). | `docs/feedback/2026-06-10-pr-pilot-v1-first-matrix.md` |
| `skill-pyeng-v1` | does `engineering-discipline:python-engineering` improve legacy-project modernization? | **Yes, and specifically:** the skill drove 5/5 doctor compliance 3/3 vs bare/generic ~2–3/5; `uv` build backend + ruff single-quote are skill-only (0% → 100%); `generic-nudge ≈ bare`, so it is the skill's content, not a generic nudge. | `docs/feedback/2026-06-13-skill-pyeng-v1-first-matrix.md` |
| `humble-vs-super-v1` | humblepowers **0.3.1** vs superpowers, mounted as plugins (5 arms) | superpowers **more effective** — regression-test discipline 90–100% vs humble 50–60% — at ~30–40% higher cost; no clean efficiency win for humble. Ceiling: 10/11 criteria at 100%. | `docs/reports/2026-06-14-humblepowers-vs-superpowers.md` |
| `humble-vs-super-v2` | re-run with humblepowers **0.4.0** (3 arms: stack-humble / super-only / stack-super) | **Verdict reversed.** 0.4.0 closed the discipline gap — regression-test 100% vs super 80% — and `stack-humble` is the **sole Pareto-optimal arm** (higher quality at ~16–20% lower cost/tokens/turns). Quality edge directional (n=10, overlapping CIs); cost edge robust. | `docs/reports/2026-06-15-humblepowers-0.4.0-vs-superpowers.md` |
| `humble-vs-super-v3`/`v4` (harder banks; v3 powered to **n=45/arm**) | can a harder bank make **correctness** discriminate? + higher-n confirmatory of the v2 verdict | **Two findings.** (1) *Harder-bank goal failed, cleanly & replicated:* opus-bare nails correctness on self-contained tasks regardless of discipline — v3 (documented edges) **and** v4 (non-local root-cause) both ceiling; **0/180 correctness failures** at n=45. The disciplines move **test-hygiene, not correctness**. (2) *v2 corrected:* at n=45 humble ≈ super on test-discipline (100% vs 95.6–97.8%, **overlapping CIs**) — v2's "humble>super" was n=10 noise. `stack-humble` still **Pareto-dominates** both super arms, but via **cost** (~9–19% cheaper, ~21% fewer turns), not quality. | `docs/reports/2026-06-16-humble-vs-super-powered-confirmatory.md` |
| `model-tier-v1` | is the series engine's complexity→model-tier mapping (0-25 Haiku / 26-55 Sonnet / 56-100 Opus) **well-tuned**? 7 tasks × 3 models, blind hard-criteria fraction, n=5 | **Over-provisions on this distribution.** On-diagonal **1/7**: Haiku aces 6/7 tasks the rubric routed to mid/strong (weak & mid bands buy **+0.00 quality** at 2–3× cost). The strong tier pays off only on the one cross-module root-cause task (`nonlocal-parse`, Haiku 40%→Opus 100%); its near-identically-scored sibling is aced by Haiku → **score ≠ model-difficulty**. Effort (`xhigh`) does **not** substitute for capacity. Caveat: bank is easy-for-Haiku. ~$20. | `docs/reports/2026-06-16-model-tier-calibration.md` |

## Open defects

- **D2 (fixed — PR11, humble-vs-super §11)** — `cost_usd_est = 0` for the subscription claude-cli adapter.
  *Real root cause* (pre-mortem finding): the adapter already parsed `total_cost_usd` onto its **adapter**
  `RunRecord`, but the **ledger** `RunRecord` had no cost field, so the value was dropped at the ledger
  boundary in `cli.py`, and `report.py` read a never-emitted `usage['cost_usd']` key. Fix: added a
  `cost_usd_est` field to the ledger `RunRecord` (additive, default `0.0`; legacy lines load unchanged —
  append-only), persisted the adapter value in `cli.py`, repointed the report's economy/efficiency USD
  column at the ledger field, and added a token×price fallback estimate in the adapter parse
  (`estimate_cost_usd`, the series engine's model-tiers rates) so subscription spawns are non-zero even when the CLI
  reports `total_cost_usd = 0`. **Billing path (resolved):** matrix spawns authenticate with the **copied
  subscription credential** (`.credentials.json`, the only file `make_isolated_config` copies into the
  temp `CLAUDE_CONFIG_DIR`); that is the intended path. Subscription auth reports `total_cost_usd = 0`
  (usage bills against the plan, not per-token), which is why the token×price estimate is the operative
  USD figure for these arms; when a real `total_cost_usd` is present (e.g. API-key auth) it is always
  preferred over the estimate. Tokens/turns/wall-clock remain the primary economy currency (C1); USD is a
  derived estimate. *Adjacent caveat — now resolved:* `make_spawn_env` (claude_cli.py) strips
  `ANTHROPIC_API_KEY` and the whole routing-diverter set (`_SPAWN_ENV_STRIP`: `ANTHROPIC_AUTH_TOKEN`,
  `ANTHROPIC_BASE_URL`, Bedrock/Vertex) from every spawn env — both spawn paths (adapter + series)
  build their env there — so a stray host key can no longer divert billing or reroute the backend.
  Historical pre-PR11 ledger lines have no `cost_usd_est`, so a regenerated scorecard shows `$0` for them
  (append-only — old lines are never rewritten). This includes the `series` arm, whose USD
  previously surfaced only because that strategy echoes the whole engine tracker event (with its own
  `cost_usd`) into `usage`; the spec-mandated repoint reads the ledger field "instead of" that key, so the
  historical series-engine USD now reads `$0` too. No recorded verdict depended on it (the series-engine bank's economy
  claim rests on tokens/sessions, C1).
- **D3 (open — routed OUT to the series engine, not a fathom defect)** — the engine wave-loop exits "All done" with
  waves still pending; `--from` mid-wave resume doesn't reschedule downstream waves.
- **[reporting]** — errored trials are excluded from the per-criterion table, so a harness-limit
  truncation (max-turns / timeout) hides real partial-compliance data; the signal was only visible by
  reading the ledger directly. Consider a distinct trial status for *budget-exhaustion* vs *task-error*
  (`src/fathom/strategies/base.py` `TrialStatus`, `src/fathom/report.py`).

## Recently fixed (context for the ledger archive)

- **Polish/self-improvement session (2026-07-05).** Audit + fixes across the measurement surfaces:
  - **Series arm was broken** — the genericize-paths change made `[tools].repo` relative (`../convoy`),
    but the invocation command is baked at resolution time and run with `cwd=workspace`, so the engine
    couldn't resolve it → smoke engine-boundary FAILED (7/8). Fixed with a shared
    `resolve_repo_invocation_cmd` helper (scenario.py) that freezes the repo to an absolute forward-slash
    path; both resolvers (cli.py, smoke.py) delegate. Smoke back to 8/8.
  - **Scorecard conflated dataset_versions** — a dv bump let old + new task versions co-render under one
    arm (last-write-wins per (scenario,task,repeat) + dv-blind `reps_for`). `report.py` now scopes to the
    current (last-appended) dataset_version and warns about excluded older-dv trials (they stay in the ledger).
  - **convoy `EXIT_BUDGET=4` / `outcome="budget"` was unhandled** — a per-spawn budget-cap halt fell
    through `_classify` to an opaque `"engine exit 4"`. Now classified explicitly (ENGINE_EXIT_BUDGET,
    clear detail; excluded from the pass rate, re-runnable, does not halt the matrix). Contract §2/§5/§7 updated.
  - **CI-honesty (blind review-panel, unanimous):** the pooled Wilson CI pools correlated repeats +
    heterogeneous tasks as independent. Kept the pooled point-and-interval (cluster-t / bootstrap collapse
    at K=1 banks and all-0/all-100 tasks — worse than Wilson) but added a concrete clustering caveat under
    Pass Rates and surfaced K (distinct tasks) beside n in each verdict — matching the calibration precedent
    (ADR-0007 D3). Panel raw output: session feedback report.
  - **Docs reconciled to as-built:** design §4.1/§4.3/§4.5/§6 (module map, "ships three", ledger-record
    schema incl. `completed` vs `complete` + the INFRASTRUCTURE state, no trial-level retry cap), CLAUDE.md
    (`[verify] timeout_s`, test-count floor), method-bindings (superpowers→humblepowers, convoy_run,
    `fathom smoke` built, wave budget), recalibration Step 0 (pr_pilot→convoy governance.py/pricing.py),
    series-toml-skeleton (contract §3 shape), pre-mortem (vela→keel), STATUS D2 caveat + In-flight.
  - **Known-but-deferred:** `infra_error` is a phantom field — report.py/calibration.py guard a field the
    producer never writes (infra trials halt with no ledger line; the real gate is `status=="completed"`).
    Dead-but-harmless; removing it ripples into the "Infra Errors" column + golden. Tracked in feedback.
- `task.limits.max_turns` was **dead config** — the adapter hardcapped at its default 30 — which
  truncated 8/9 trials of the first `skill-pyeng-v1` run (archived invalid). Now plumbed through
  `Runner.execute`; the task budget is 80.
- The verifier loaded the candidate module by file-path (no parent package), so a valid src-layout
  refactor using a relative import was graded a behavior failure. Now imports as a package.

## In flight

- *(nothing in flight)* — the `humble-vs-super` plugin-eval is complete through **four** analyses (v1
  0.3.1 baseline, v2 0.4.0 re-run, v3+v4 harder-bank retunes with the v3 powered confirmatory at n=45/arm;
  see Analyses run). Spec + instrument: `docs/specs/2026-06-14-fathom-humble-vs-super-design.md`, the
  keel-DoR-certified design; 11-PR build series in `pr-series/humble-vs-super/`. The four ledgers
  (`ledger/humble-vs-super-{v1,v2,v3,v4}.jsonl`), the v3/v4 banks, scenarios,
  `tests/test_verify_humble_super_v{3,4}.py`, and `docs/reports/2026-06-16-...md` are **committed**.
- **Model-tier calibration study (2026-06-16) — complete.** New instrument: the `model-tier-v1` bank
  (8 graded hard-criteria tasks + `scores.toml` w/ blind re-rating), `scenarios/model-tier/`, the
  `src/fathom/calibration.py` report views (§7/§8 — confusion matrix, dose-response, **corrected** strict
  Pareto), the `--max-budget-usd` per-spawn cap (§11), `tests/test_{calibration,cli_budget,verify_model_tier}.py`,
  and the `model-tier-effort` sub-study. keel-DoR-certified spec
  (`docs/specs/2026-06-16-fathom-model-tier-calibration-design.md`, 4 pre-mortem rounds) + ADR-0007.
  Verdict in Analyses run (mapping **over-provisions** on this distribution). **The pairwise judge (§6)
  was deferred** (verifier-only spine — reinforces next-step #2). `ledger/model-tier-{v1,effort}.jsonl`
  + `docs/reports/2026-06-16-model-tier-calibration.md` are **committed**.
## Next steps (highest-leverage first)

1. **A discriminating *correctness* bank — now known to be hard (v3/v4 finding).** Two harder-bank
   designs (v3 documented-edge, v4 non-local root-cause) **both ceilinged**: opus-bare nails correctness
   on self-contained, deterministically-verifiable tasks (0/180 failures at n=45), so the bare pass-rate
   sits at the *correctness* ceiling, and the only axis that discriminates is test-hygiene
   (`regression_test_present`). To make **correctness** carry signal would require either a harder task
   *class* — large multi-file navigation where a one-shot can't hold the whole codebase (measures
   context-management as much as discipline; big authoring lift) — or a *weaker base model* (the
   disciplines may move correctness there). The cheaper lever for a broader quality axis is next-step 2.
2. **Light up the pairwise judge.** `src/fathom/grading/judge.py` ships dark (built and unit-tested, not
   wired into any verdict). It is the **quality axis** — architecture / readability beyond the
   verifier's mechanical checks. Wiring requires validating the judge on our own tasks first (ADR-0003,
   design §4.6); fuzzy-rubric gold-set κ is weak evidence, so prefer verifier-expressible criteria where
   possible.
3. **D2 cost fix** (above) — unblocks cross-arm USD economy claims.
4. **(v2, deferred / interface-ready)** OTel telemetry join; non-Claude runner adapters; Docker-isolated
   workspaces (would lift the offline presence-only grading limit, C3); migrating the trigger-axis
   (recall/specificity) evals from craft-collection `evals/`.
