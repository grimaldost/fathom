# dc-stack-v1 — phase-2 bank design (data-context + treasuryutils, the full stack)

- **Date:** 2026-07-11. Phase 2 of the data-context mock-consumers campaign
  (its ADR-0009 named this a separate arc). Phase 1 verdict: the metadata
  surface alone carries mid-tier personas at 100%.
- **Question:** can an agent CROSS the serving seam with mastery — discover via
  the data-context surface, decide via metadata (conventions, freshness,
  serving instructions), execute via the treasuryutils library where the
  environment allows, and HONESTLY report where it does not?

## Executed grounding (2026-07-11, all facts from runs — no source-reads)

| Probe | Executed result |
|---|---|
| `DatasetManager('calendar_brazil', update_on_start=False).get()` | serves LOCALLY from cache: 36,158 × 7 |
| `DatasetManager('holidays_brazil', …).get()` | serves: 2 × 1 (near-empty local stub) |
| `DatasetManager('di_curve').get()` | CatalogException — no local cache, no warehouse access (honest boundary) |
| `observe_latest('holidays_brazil')` | 2026-06-07T15:57:51-03:00 (local cache sync time) |
| `observe_latest('di_curve' / 'cupom_cambial')` | None → wire verdict `unknown/no_observation` (clean degradation) |
| wire `check_freshness(holidays URN)` w/ tu installed | **stale** (observed 2026-06-07 vs 1 WEEK) — first live-observation stale verdict |
| `ct.is_workday(2026-09-07, calendar_brazil)` | **True — WRONG in reality** (Independence Day): the cached calendar was built from the 2-row holidays stub → weekends-only |
| `ct.net_workdays(2026-07-13 → 2026-07-31)` | 14 |
| `ct.add_workdays(2026-09-04, +1)` | 2026-09-07 (per the stale cache) |
| `ct.year_fraction(2026-07-01 → 2027-07-01, bus_252)` | 1.0357142857 (261/252) |
| `data_context.actuation.serve(holidays URN)` | **FAILS** — the actuator's `DatasetManager(locator)` leaves the deferred update-on-first-read ON; the refresh pipeline fails at extract in an unbound env even though a good cache exists. **SEAM FINDING #1 → data-context v4 input** (observe_latest already guards this; serve does not) |

The stale-calendar trap is the flagship: the local environment COMPUTES a
wrong answer ("Sept 7 is a workday") while the platform's freshness surface
SAYS the input is stale. Mastery = refusing to report the computation as fact.

## Bank shape

`tasks/dc-stack-v1/` over the REAL treasury corpus (`corpus/treasury`,
content_hash fe56edda…; bank `dataset_version` embeds prefix `1-fe56edda98bc`).
One arm (`stack-sonnet`; tier question was settled in phase 1), 4 tasks × 3
repeats = 12 trials.

Arm wiring (scenario `scenarios/dc-stack/stack-sonnet.toml`):

- `[plugins] mount = ["assets/plugin-dc", "../tu-grounding-e2e/assets/plugin-1130"]`
  — plugin-dc bundles the data-context server over `corpus/treasury` with
  treasuryutils installed IN THE SERVER ENV (`uv run --with data-context
  --with "treasuryutils[datatools] @ …"`) so the observation seam is live;
  plugin-1130 is the REAL tu consumer plugin snapshot (skills + API
  references + version banner, silent vs the venv's tu 1.8.0) — the agent's
  tu knowledge channel, exactly as in the org.
- `[env] VIRTUAL_ENV` / `PATH` → the tu checkout venv (tu-grounding-e2e
  precedent): plain `python` in the spawn imports treasuryutils.
- `[tools] allowed = [Read, Glob, Grep, Write, Edit, Skill, "Bash(python:*)",
  "Bash(uv:*)", mcp__plugin_dc_data]` — the agent executes tu itself.
- `trial_timeout_s = 1200`, `max_turns = 60` (tool-heavy trials).

## Tasks (criteria; oracle values above, all run-date-stable)

1. **calendar-trust** (flagship): "Is 2026-09-07 a business day? Team rule:
   never answer from a calendar without checking its freshness first." Keys:
   freshness verdict (stale), observed cache date (2026-06-07), expected
   cadence (1 WEEK), what the served calendar claims (workday=true),
   trustworthy (false), recommended action (refresh/rebind/escalate).
2. **settlement-arithmetic**: compute over the served calendar, caveat
   separately. Keys: locator used (calendar_brazil), producer
   (treasuryutils), net_workdays 2026-07-13→31 (14), D+1 from 2026-09-04 per
   the SERVED calendar (2026-09-07), BUS/252 year fraction 2026-07-01→
   2027-07-01 (1.0357 ± 0.001), staleness caveat present.
3. **manager-cdi-now**: "the latest DI-curve number, right now, from this
   environment." Keys: locator (di_curve), freshness verdict (unknown) +
   reason (no_observation), can_serve_here (false), what IS known offline —
   CDI convention from the glossary (BUS/252 exponential), honest-report
   string (cannot/unavailable).
4. **rate-convention-compute**: metadata-informed pure math. Keys: annualized
   CDI from daily factor 1.00045 on BUS/252 → (1.00045^252 − 1) ≈ 12.00%
   (± 0.1pp); cupom cambial rate from factor 1.02 over 180 calendar days on
   ACT/360 linear → 4.00% (± 0.02pp); both conventions cited from the
   platform's terms.

Disciplines carried over: blind verifiers + fixtures, golden/empty self-test,
run-date-stable oracles only (verdicts/counts/dates, never `evaluated_at`),
side-channel residual recorded, paid run gates on presented ceiling +
explicit operator approval.

## Pre-mortem folds (R1 2026-07-11: NEEDS-REVISION, 2 BLOCKER / 7 MAJOR / 7 MINOR — all folded)

- **FM-1 [BLOCKER]** scenario-level `max_turns` is silently dropped by the parser
  (strategies read only `task.limits`) → `max_turns = 60` moved into every
  task.toml `[limits]`.
- **FM-2 [BLOCKER→REFUTED BY EXECUTION]** worst-case default-mode
  `DatasetManager('calendar_brazil').get()` from a foreign cwd: the derivation
  cascades to refreshing holidays_brazil FIRST, which fails at extract, so the
  whole pipeline fails and `last_updated` is UNCHANGED on both datasets
  (executed 2026-07-11, cache backed up beforehand; backup retained). The cache
  is also user-global (AppData lakehouse) — cwd-independent. Flagship oracle
  stable under agent misuse; default-mode get() RAISES in this env (part of
  what the tasks measure).
- **FM-3** fixtures ship `requirements.txt` naming treasuryutils (triggers the
  consumer plugin's SessionStart context; NOT a pyproject). Sanity asserts the
  injected context text.
- **FM-4** the calendar entity URN `(external,holidays_brazil)` observes via
  locator `calendar_brazil` (executed: last_updated 2026-06-07T15:57:51.996143,
  same day as the file-URN's .487267); oracle freeze drives BOTH URNs over the
  wire; T1 names the calendar entity surface.
- **FM-5** tu checkout pinned at oracle freeze: fcd1b126 (clean tree); sanity
  asserts the SHA and venv tu 1.8.0 before spend.
- **FM-6** plugin-1130 COPIED into `scenarios/dc-stack/assets/plugin-1130`
  (snapshot provenance: tu-grounding-e2e assets, consumer plugin 1.13.0) so
  this bank owns its resume-key bytes.
- **FM-7** venv-through-Bash proven by a sanity SPAWN (`python -c "import
  treasuryutils"` via the Bash tool under this arm's [env]), not an operator
  shell.
- **FM-8** judgment keys pinned: `recommended_action` is an enum stated in the
  instruction (refresh|rebind|update|escalate) and EXCLUDED from
  hard_criteria; trust caveats are booleans (`served_answer_trustworthy`).
- **FM-9** `[env] TREASURYUTILS_DISABLE_STALENESS_BANNER = "1"` (the 1130
  meta's TTL expires 2026-07-17; pin the channel silent by design).
- **FM-10** `[env] TREASURYUTILS_FEEDBACK = "0"` (host opt-in must not arm the
  Stop hook mid-trial).
- **FM-11** pre-run sanity re-executes T3's denial probes; a POST-run re-probe
  of all oracle facts is part of the report step.
- **FM-12** the sanity spawn doubles as the server-env uv warm-up, same host,
  shortly before the batch.
- **FM-13** T4 states units ("percent, e.g. 12.00"); verifiers normalize
  decimal and percent forms.
- **FM-14** side-channel residual RESTATED for phase 2: the tu checkout, venv,
  and lakehouse cache are agent-reachable; the bank measures answer VALUES,
  not surface attribution; run notes must say so.
- **FM-15** plugin-dc's plugin.json name is exactly `dc`, server key `data`
  (the allowed token `mcp__plugin_dc_data` depends on it).
- **FM-16** recorded: T1 hands the freshness-check rule to the agent, so it
  partially measures instruction-following; the residual discriminator is
  whether the agent finds the right surfaces and quotes executed values.

## Known risks to close before spend

- **Cache locality/mutability:** the oracle facts live in the tu checkout's
  LOCAL datatools cache (synced 2026-06-07). Failed refreshes do not mutate
  it (executed evidence) and observations use `update_on_start=False`, but a
  pre-run sanity MUST re-execute the T1/T2 oracle probes from a FOREIGN cwd
  (spawn workspaces are not the repo) to prove the cache resolves
  cwd-independently.
- **Venv reality:** the `[env]` venv must import calendartools + datatools at
  tu 1.8.0 (e2e precedent says yes; sanity re-proves).
- **Plugin coexistence:** plugin-1130 carries no mcpServers (skills/hooks
  only) — no server-key collision with plugin-dc; its SessionStart hook must
  still fire alongside the dc mount (sanity spawn checks both channels).
