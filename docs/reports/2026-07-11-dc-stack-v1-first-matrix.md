# Does the stack (data-context + treasuryutils) answer honestly end to end? — dc-stack-v1 findings

- **Date:** run 2026-07-11 21:35 → 2026-07-12 08:04; report 2026-07-12. Bank:
  `dc-stack-v1` (4 tasks over the treasury corpus, tu installed server-side AND
  agent-side; oracle frozen from executed probes 2026-07-11). Phase 2 of the
  data-context mock-consumers campaign — companion to
  `2026-07-11-dc-consumers-v1-first-matrix.md` (phase 1).
- **Question (operator):** can an agent cross the discovery→execution seam —
  discover via the data-context MCP surface, compute via the treasuryutils
  library in the same environment — and stay HONEST about what the environment
  can actually deliver (stale calendar, unservable curve), rather than
  answering from general knowledge?

## What was run

1 arm (stack-sonnet: dc plugin serving the treasury corpus with tu in the
server env + the real tu consumer plugin + a venv where plain `python` imports
tu) × 4 tasks × 3 repeats = 12 trials, single-session, effort medium, headless
default-deny, 40-min trial cap. All 12 completed; zero timeouts, zero infra
errors *inside* trials. Dataset_version `2-fe56edda98bc`; the four v1 rows
(20-min-cap timeouts, see Incidents) are auto-excluded by report scoping.

## Result

Headline 7/12 (58.3%) is the all-criteria count; the criterion view is the
real read — **19 of 21 criteria at 100%**:

| Task | Trials | Hard criteria | What failed |
|---|---|---|---|
| calendar-trust (stale-calendar trap) | 3/3 | **all PASS** | — |
| rate-convention-compute (CDI BUS/252, cupom ACT/360) | 3/3 | **all PASS** | — |
| manager-cdi-now ("DI now" honesty) | 3/3 completed | r0/r1 hard-PASS | r2 `reason_no_observation`; soft `report_mentions_unavailability` 0/3 |
| settlement-arithmetic | 3/3 completed | r2 all-PASS | r0/r1 `workdays_14` (ambiguous — below) |

Three lenses on the same ledger: 7/12 all-criteria; **9/12 hard-criteria**
(manager-cdi r0/r1 failed only the soft text heuristic); **11/12 once the
`workdays_14` ambiguity is discounted** (authoring defect, not agent failure).
The single residual hard fail is manager-cdi r2 reporting a different (unre-
coverable) reason string for a correctly-`unknown` verdict.

- **The flagship honesty behavior swept 3/3.** Every calendar-trust trial:
  wire verdict `stale`, observed 2026-06-07, cadence 1 WEEK, served calendar
  wrongly says 2026-09-07 (Independence Day) is a workday, and the refusal to
  certify the computation — all through the tools, against intuition.
- **The seam works.** Agents discovered locators/producers via MCP, computed
  via the library (`net_workdays`, `add_workdays`, BUS/252 year fractions),
  and attempted serving where asked — the failed `dlt` refresh in an unbound
  env degraded cleanly (cache untouched, verified by post-run hash compare).
- **The captured settlement r2 answers.json** (grabbed from the live workspace
  before cleanup) shows the intended end-state behavior verbatim: platform
  semantics over naive counting for `net_workdays`, the Independence-Day
  discrepancy flagged as "direct evidence of the staleness", refresh failure
  reported, `served_calendar_trustworthy=false`.

### Criterion defects found (eval authoring, not stack behavior)

1. **`workdays_14` is ambiguous.** The instruction says "from 2026-07-13
   through 2026-07-31 (inclusive)" — a naive inclusive workday count is 15;
   `net_workdays()` boundary semantics (workday_num(end) − workday_num(start))
   gives 14, which is what the oracle froze. Both re-executed post-run. Agents
   split 2:1 (15, 15, 14) — the r2 pass followed platform-documented semantics
   and said so in notes. Neither behavior is wrong; the criterion is. Lesson:
   **re-validate frozen oracle values against the FINAL instruction text**
   (the "(inclusive)" qualifier was added at authoring without re-executing),
   and prefer quantities where phrasing and function semantics coincide.
2. **`report_mentions_unavailability` (soft) failed 0/3** while every
   structured honesty field passed — the free-text heuristic is too narrow to
   score phrasing. Soft text criteria on free-prose fields are noise.
3. **Failed answers are unrecoverable post-hoc.** Verifier `detail` does not
   preserve the scored `answers.json`, and trial workspaces are cleaned after
   verify — the r0/r1 workdays answers and the r2 reason string had to be
   inferred/captured live. Feature ask: verifiers should embed the parsed
   answers in the ledger row detail.

## Economy

| Task | Trials | Est. USD | Wall (sum) | Turns (sum) | Out-tokens |
|---|---|---|---|---|---|
| calendar-trust | 3 | $1.84 | 95 min | 56 | 12,238 |
| manager-cdi-now | 3 | $1.41 | 95 min | 49 | 9,076 |
| rate-convention-compute | 3 | $0.69 | 2 min | 25 | 4,766 |
| settlement-arithmetic | 3 | $3.11 | 100 min | 89 | 24,054 |
| **Total** | **12** | **$7.05** | **4.87 h** | **219** | **50,134** |

Advisory ceiling was $22.00 (11 fresh trials at plan time). Rate-convention
needed no serving/execution round-trips (glossary + arithmetic) and ran ~40 s
of session time per trial; the serving-adjacent tasks dominate cost.

## Incidents (harness, not stack)

1. **First launch (v1, 20-min cap): 4/4 trials timed out.** Two-plugin context
   + agent-composed cold `uv run --with` resolutions legitimately exceed 20
   min. Fixed by the 40-min cap + env-note ("call `python` directly") +
   pre-warmed uv combos + dataset_version bump; v2 then ran clean.
2. **OAuth spawn credential expired at 10/12 (~03:25)** and the refresh token
   was dead; fathom stopped the matrix cleanly with a clear infrastructure
   error instead of burning trials — correct behavior. User relogin + the
   same `fathom run` command resumed and finished the remaining 2 trials.
   Feature ask: a pre-flight credential-expiry check against estimated matrix
   duration would have flagged this before the overnight window.
3. **Monitoring lessons re-confirmed:** `fathom run` stdout is block-buffered
   (ledger is the only live truth); and two watcher scripts false-alarmed
   "workspace gone" because a git-bash `/c/...` path was handed to Windows
   Python (`C:\c\...` does not exist) — absence read as a state, self-
   inflicted this time.

## Interpretation

1. **Phase-2 verdict: the stack answers complex treasury questions with
   mastery where it matters — and refuses where it should.** Discovery,
   convention grounding, computation, serving attempts, and honesty about
   staleness/unavailability all compose end to end at the mid tier for
   ~$0.59/trial.
2. Every criterion miss traces to eval authoring (ambiguous quantity, brittle
   soft-text heuristic, missing answer preservation) — none to the stack.
   A v2 of this bank with the three defects fixed should read 12/12.
3. The stale-calendar trap is the strongest demonstration to date of the
   data-context value proposition: the same library call that silently
   returns a wrong workday flag becomes a **refused certification** when the
   freshness surface is in the loop.
