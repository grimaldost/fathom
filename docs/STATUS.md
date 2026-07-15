# fathom — status & next steps

*The index of what's been run, what's open, and what's next. Per-run detail lives in the run notes
and findings reports under `docs/reports/`; this file points at them. Update it when a run or a
defect changes state.*

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
| the series-engine bank | single long session vs the series engine's multi-session series vs bare, on 3 dev tasks | the series engine's pipeline gave **no quality gain** over a bare single session at ~4.6× tokens and 8 sessions/trial — the tasks sat below the coordination threshold (ceiling effect: bare 6/6). | `docs/reports/2026-06-10-pr-pilot-v1-first-matrix.md` |
| `skill-pyeng-v1` | does `engineering-discipline:python-engineering` improve legacy-project modernization? | **Yes, and specifically:** the skill drove 5/5 doctor compliance 3/3 vs bare/generic ~2–3/5; `uv` build backend + ruff single-quote are skill-only (0% → 100%); `generic-nudge ≈ bare`, so it is the skill's content, not a generic nudge. | `docs/reports/2026-06-13-skill-pyeng-v1-first-matrix.md` |
| `humble-vs-super-v1` | humblepowers **0.3.1** vs superpowers, mounted as plugins (5 arms) | superpowers **more effective** — regression-test discipline 90–100% vs humble 50–60% — at ~30–40% higher cost; no clean efficiency win for humble. Ceiling: 10/11 criteria at 100%. | `docs/reports/2026-06-14-humblepowers-vs-superpowers.md` |
| `humble-vs-super-v2` | re-run with humblepowers **0.4.0** (3 arms: stack-humble / super-only / stack-super) | **Verdict reversed.** 0.4.0 closed the discipline gap — regression-test 100% vs super 80% — and `stack-humble` is the **sole Pareto-optimal arm** (higher quality at ~16–20% lower cost/tokens/turns). Quality edge directional (n=10, overlapping CIs); cost edge robust. | `docs/reports/2026-06-15-humblepowers-0.4.0-vs-superpowers.md` |
| `humble-vs-super-v3`/`v4` (harder banks; v3 powered to **n=45/arm**) | can a harder bank make **correctness** discriminate? + higher-n confirmatory of the v2 verdict | **Two findings.** (1) *Harder-bank goal failed, cleanly & replicated:* opus-bare nails correctness on self-contained tasks regardless of discipline — v3 (documented edges) **and** v4 (non-local root-cause) both ceiling; **0/180 correctness failures** at n=45. The disciplines move **test-hygiene, not correctness**. (2) *v2 corrected:* at n=45 humble ≈ super on test-discipline (100% vs 95.6–97.8%, **overlapping CIs**) — v2's "humble>super" was n=10 noise. `stack-humble` still **Pareto-dominates** both super arms, but via **cost** (~9–19% cheaper, ~21% fewer turns), not quality. | `docs/reports/2026-06-16-humble-vs-super-powered-confirmatory.md` |
| `model-tier-v1` | is the series engine's complexity→model-tier mapping (0-25 Haiku / 26-55 Sonnet / 56-100 Opus) **well-tuned**? 7 tasks × 3 models, blind hard-criteria fraction, n=5 | **Over-provisions on this distribution.** On-diagonal **1/7**: Haiku aces 6/7 tasks the rubric routed to mid/strong (weak & mid bands buy **+0.00 quality** at 2–3× cost). The strong tier pays off only on the one cross-module root-cause task (`nonlocal-parse`, Haiku 40%→Opus 100%); its near-identically-scored sibling is aced by Haiku → **score ≠ model-difficulty**. Effort (`xhigh`) does **not** substitute for capacity. Caveat: bank is easy-for-Haiku. ~$20. | `docs/reports/2026-06-16-model-tier-calibration.md` |
| `context-size-v1` (4 matched small/large pairs) | does interdependence at *volume* (~40 coherent distractor modules) push the empirically-right tier above the identical ≤5-file fix? haiku + opus, n=5, hard-criteria fraction, GO-gated pilot | **No — synthetic volume does not bite.** Haiku 100% on all 8 tasks (both sizes, incl. the score-64 nonlocal pair; ~328k cache-tokens/trial — it ingests the volume); all 4 pairs weak = weak; **NO-GO** at the pilot gate → the sonnet arm + n=5 fill deliberately unrun (~$10.2 spent; ~$120 remaining ceiling saved). Over-provisioning **persists at volume**; opus +0.00 quality at ~4.2× cost. Caveat: shallow synthetic distractors — a real-codebase probe is the phase-2. | `docs/reports/2026-06-16-context-size-calibration.md` |
| `model-tier-v1` + `sonnet5` arm | does the over-provisioning verdict hold after convoy bumped mid Sonnet 4.6 → **Sonnet 5**? (35 fresh trials; the June cells resume-reused free) | **Reproduces** (on-diagonal 1/7). `fix-nonlocal-parse` is still the one discriminator; Sonnet 5 climbs its ladder 40→60→**80**→100% (Haiku/S4.6/S5/Opus), so the strong tier trends escalation-only. **No threshold change**; the calibration note was extended instead. Cost caveat: Sonnet 5's est $/trial landed **above** Opus's (new tokenizer, adaptive thinking) — report tokens beside $. ≈$11.4 est / ~$0 real. | `docs/reports/2026-07-01-model-tier-recalibration.md` |
| `ablation-v1` (querytable, greenfield) | value-side ablation instrument v1: can a defect-escape bank make bare fail, so the gate/review arms have escapes to catch? | **Quality-null, by instrument:** greenfield + single-file left no regression surface — bare Sonnet 5 aced it, nothing to catch. Superseded by the brownfield v2 instrument. | design: `docs/specs/2026-07-01-pr-pilot-full-ablation-design.md` (superseded); ledger `ledger/ablation-v1.jsonl` |
| `ablation-v2` (exprlang, brownfield) | do convoy's engine-independent features (gate / review / authoring / tier ladder) add quality on brownfield multi-file work? 15 arms, n=6–10, blind 15-criterion oracle | **Strong-tier null:** bare Sonnet 5 self-gates to 100%; every in-session feature adds +0. **Weak tier (Haiku):** failures collapse onto a type-contract class the visible suite misses (8/8 gates green, 5/8 oracle escapes); a strengthened gate coincided with 38%→90%, attributable lift bounded **+20..+52pp** (batch-confounded). Transferable: **self-authored tests inherit the implementer's blind spots — gate value tracks oracle independence + coverage.** Engine arm not run. ~$0 real. | `docs/reports/2026-07-01-pr-pilot-ablation-v2-findings.md` (companion analysis: `docs/reports/2026-07-01-pr-pilot-beyond-the-engine.md`) |
| series-usefulness (task `sheet`; bank retired — ledger archived) | did Sonnet 5 move the orchestration threshold? a single `bare-sonnet5` difficulty ladder, dv1 (9 crit) + dv2 (15 crit), n=5, property-graded | **Bare aced both probes (5/5, 5/5)** — it one-shots a fill-and-aggregates reactive spreadsheet engine → **the threshold moved up substantially**. With the 2026-06-10 result (engine ~4.6× tokens, 8 sessions/trial, +0.00 quality), the engine is **overhead for self-contained feature work**; defect-escape was unobservable (bare never failed). ≈$13 est / ~$0 real. | `docs/reports/2026-07-01-pr-pilot-usefulness-findings.md` (ledger: `ledger/archive/pr-pilot-usefulness-v1.jsonl`) |

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

### Open items swept from the feedback corpus (2026-07-09)

The dogfooding feedback reports were relocated out of the repo (to the local, gitignored
`feedback/` dir); before the move, every proposed promotion was checked against the code and the
still-open ones are tracked here so they survive the relocation. Two were confirmed **resolved** in
the meantime: the efficiency-view Pareto flag is now strict non-domination (`report.py`), and the
series invocation-path regression guard (`TestRepoInvocationCmd`) runs in CI via `pytest`
(`fathom smoke` itself stays a manual gate — credentialed and paid).

**Triage (2026-07-09, `feedback/2026-07-09-triage-v1.md`).** The 7-report corpus was clustered and
gated; three clusters cleared for build (leverage-ordered), the rest hold at `watch` in the table
below pending a second corroborating report:
1. **Report legibility** — the headline all-truthy pass-rate ceilings the signal; promote the
   hard-criteria/partial-credit fraction into the *core* report, add all-arms to the calibration
   view, and allow rendering a chosen historical `dataset_version` (`report.py`/`calibration.py`).
2. **Analysis close-out** — a committed ledger with no STATUS row / `docs/reports/` entry (and its
   decisions) goes invisible; the prose step shipped (`CONTRIBUTING.md`) and recurred, so escalate
   to a mechanical `fathom report` warn when a bank's ledger has no matching report (`cli.py`).
3. **Smoke-gate robustness** — the gate can pass hollow under an expired credential (a check
   satisfied by absence) or crash on a non-cp1252 char; fail fast as INFRA-BLOCKED and force UTF-8
   on stdout (`smoke.py`, `cli.py`).

| Item | Sev | Home |
|---|---|---|
| `fathom smoke` doesn't plumb `--effort`/`--model`, blocking effort-acceptance probes before a paid effort run | MED | `src/fathom/cli.py` (smoke subparser) |
| No forced UTF-8 on harness stdout: a spawn emitting a non-cp1252 char can still crash `smoke`/`run` prints on a cp1252 console (smoke's own literals were de-mojibaked; `reconfigure(errors="replace")` was not added) | MED | `src/fathom/smoke.py`, `src/fathom/cli.py` |
| No token-TTL pre-flight: an hours-long matrix can outlive the subscription OAuth token (two manual re-auths on the v1 100-trial run) | MED | `src/fathom/cli.py` (run path) |
| Hard-criteria quality fraction — the anti-ceiling metric — renders only for calibration banks (`scores.toml` + `hard_criteria`); promote it to the core report for all banks | MED | `src/fathom/report.py` (reference impl in `calibration.py`) |
| No warning when task content (instruction / `verify.py` / fixtures) changes without a `dataset_version` bump — silent stale-resume risk | LOW | `src/fathom/taskbank.py` / run planner |
| `fathom report` rejects `--scenarios-dir` while `run` requires it; it re-derives arm names from the ledger `scenario` field — accept the flag or document the asymmetry | LOW | `src/fathom/cli.py` |
| `--no-engine-boundary` reads as disabling a safety control; it only skips a check group — rename (e.g. `--skip-engine-check`) or document | LOW | `src/fathom/cli.py` |
| `_CEILING_PER_TRIAL_USD = 2.00` is flat; observed actuals run ~$0.08–0.59/trial by strategy — recalibrate per strategy | LOW | `src/fathom/cli.py` |
| A re-vendored plugin copied into the wrong (un-suffixed) dir is silent — the run uses the old plugin; warn when a mounted dir's `@version` disagrees with its `plugin.json` | LOW | `src/fathom/cli.py` |
| `fathom run` emits no closing summary line (`N trials completed, $X spent`); headless captures must read the ledger for cost | LOW | `src/fathom/cli.py` |
| No deliberate way to render a chosen *historical* `dataset_version` now that the report scopes to the current one | LOW | `src/fathom/cli.py` / `report.render` |
| Design-effect-inflated Wilson as a mechanical guard on the pooled CI, if the advisory K + caveat proves insufficient | LOW | `src/fathom/report.py` |
| Dangling ADR references lost in the 2026-07 history squash: `ADR-0008` (cited by the context-size bank docs) and `ADR-0009` (cited by the usefulness / beyond-the-engine docs) exist in neither fathom nor convoy, and `docs/concepts.md` was never created — recover the lost ADR content from the citing docs or de-reference | LOW | `tasks/context-size-v1/{README.md,scores.toml}`, `docs/reports/2026-07-01-pr-pilot-{usefulness-findings,beyond-the-engine}.md`, `docs/specs/2026-07-01-pr-pilot-usefulness-v2-design.md` |

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
  `tests/test_verify_humble_super_v{3,4}.py`, and `docs/reports/2026-06-16-humble-vs-super-powered-confirmatory.md` are **committed**.
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
3. **(v2, deferred / interface-ready)** OTel telemetry join; non-Claude runner adapters; Docker-isolated
   workspaces (would lift the offline presence-only grading limit, C3); migrating the trigger-axis
   (recall/specificity) evals from craft-collection `evals/`.
