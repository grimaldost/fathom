# fathom — improvement backlog

The leverage-ordered list of what to change next, and what deliberately not to. It is the backlog of
record: `docs/STATUS.md` keeps the analysis index and the open-defect narrative, but its two open-item
tables (the 2026-07-09 feedback sweep and the "Next steps" list) predate this pass and should be
refreshed against this file by hand.

Compiled 2026-08-11 from four inputs, tagged per item:

- **[triage]** — the dogfooding feedback corpus, triaged 2026-08-11 across 11 reports (rows T9–T15),
  carrying forward the still-open rows of the two earlier passes (T1–T8). Every row was checked
  against the working tree at `2211f2d`.
- **[review]** — a feature-by-feature review of the shipped surface (CLI, plugin, banks, docs) against
  the current native Claude Code baseline and the named alternatives.
- **[research]** — two August 2026 briefs: the competitive landscape for eval harnesses, and what the
  harness now does natively.
- **[cross-review]** — a 2026-08-11 consistency pass across the sibling backlogs (the craft collection,
  keel, convoy, mantis-research). It adds notes to existing items and two new rows; it reorders nothing.
  Where it disagrees with an item's standing argument, the note sits beside that argument rather than
  replacing it.
- **[wave-2 run] / [wave-3 run]** — defects the 2026-08-11 and 2026-08-12 measurement waves walked
  into in field use, added after this file was compiled. They are not proposals read out of a corpus:
  each names the run that paid for it, so the evidence line is an observation rather than a citation.

Item shape: a stable ID, a one-line claim, the cause and its evidence, the proposed change, an effort
estimate (**S** — one focused change; **M** — a small series with tests; **L** — a design decision plus
a multi-PR series), and the source tag. Feedback reports are cited by their corpus stem. Where the
triage and the review disagree, the item says so rather than quietly picking a side.

## Shipped in the 2026-08-11 instrument-trust wave (`backlog/wave-1`)

The Now section's instrument-trust rows, in the order they were built. Each item below
carries its inline status; the entries are kept in place rather than deleted so the
argument that motivated them stays readable beside the change that answered it.

- **FATH-B01 — SHIPPED.** `fathom.streams` (packaged stream-json reader) + `fathom.arming`
  (four-axis verification) + `fathom.armingprobe` (one cheap real spawn per declaring arm)
  + `fathom verify-arming` + a pre-flight in `fathom run` that refuses with `EXIT_UNARMED`
  (11). Reverting `verify_arming` to the pre-fix "declaration is proof" behaviour turns 15
  tests red, including the recorded serena-nav BLOCKER. One false positive found and fixed
  on the first live run: ambient account-level MCP connectors leak into the isolated spawn
  and were being charged to arms that never declared them.
- **FATH-B02 — SHIPPED.** `fathom validate <bank>` (free) + a pre-flight in `fathom run`
  refusing with `EXIT_BANK_INVALID` (12). Two false positives found by running it against
  the real banks and fixed before trusting it: property 1 now reads the verifier's
  **criteria** rather than its exit code (`skill-pyeng-v1`, the strongest-discriminating
  bank in the corpus, was being reported unmeasurable), and property 3 refuses only when
  the gate cannot execute at all, warning rather than failing on a red baseline
  (`ablation-v2`'s visible suite encodes its target feature, so its baseline is red by
  design). **Not claimed:** the triad cannot catch a bank whose tasks are simply too easy —
  that ceiling stays authoring judgement, exactly as this item's own split says.
- **FATH-B03 — SHIPPED.** A trial row drops its criteria and carries `valid=false` unless
  `status == "completed"`. Additive; no committed line rewritten.
- **FATH-B05 — SHIPPED (core).** Economy and Efficiency carry per-cell N and per-trial
  min/median/max for tokens and turns; the Pareto star renders as a contested `★?` with a
  footnote when the arms' per-trial ranges overlap; a new Arm Health table names trials at
  or over `max_turns` and states that such an arm's pass rate is a lower bound. **Deferred:**
  the successful-`mcp__*`-invocation count per arm, because it needs stream data that is
  opt-in (`FATHOM_STREAM_DIR`) and absent from most committed runs — `fathom.streams` now
  packages the parsing, so this is a small follow-up rather than new work.
- **FATH-B06 — SHIPPED.** All five open analyses written up under `docs/reports/`, in the
  order the cross-review specifies. **Deferred:** the `fathom report` warn and the CI gate
  that would prevent recurrence — the five write-ups were the live dependency; the ratchet
  is the follow-up.

Two rows shipped from **Next** because the paid run walked into them:

- **FATH-B14 — SHIPPED.** The verifier's `stdout`/`stderr` are persisted on the trial row (bounded
  at 4096 chars, since the ledger is committed). Promoted mid-wave: a $2.00 trial errored with
  `verifier error: non-JSON/crash` and the reason was unrecoverable, which is precisely the cost
  this row predicted.
- **A verifier-protocol defect found by that same trial, not previously on the backlog.** A verifier
  that checks behaviour-preservation must import the agent's modified package, so anything that
  package prints at import time lands on stdout ahead of the JSON — and the whole-stdout parse threw
  the trial away. The discard is **arm-correlated**: whether the agent adds a print is a property of
  the arm, so an arm that writes chattier code loses more trials. That is a silent bias, not merely
  a lost trial. `extract_criteria` now takes the last JSON object on stdout. Reproduced locally
  before fixing; absence of any object is still an error. **`fathom validate` cannot catch this
  class**, because validation only ever runs the verifier against the *unmodified* fixture — worth
  writing into FATH-B10's bank-design reference when it is split.

Two rows moved by evidence this wave rather than by argument:

- **FATH-B20** is now urgent, not S-effort housekeeping. `tasks/serena-nav-v1/` and
  `-v2/` hold no bank and no ledger, so the arming defect that motivated FATH-B01 **cannot
  be re-measured at all** — the instrument is fixed and the experiment is unrecoverable.
- **FATH-B19** partially addressed: `fathom report` now takes `tasks_dir` (needed for the
  turn caps). `--scenarios-dir` / `--ledger-dir` are still not threaded.

### Cross-project gate status after this wave

Recorded here because four sibling backlogs read this file for it.

| Gate | Verdict | Evidence |
|---|---|---|
| **CRAF-B01** (flagship skills vs no-skill baseline) | **confirmed, and it points away from retirement** for `python-engineering` — now **at the merged version**; **un-invalidated but NOT re-validated** for the process-discipline banks | `docs/reports/2026-08-11-skill-pyeng-v1-revalidation.md`, then `…-merged-content-rerun.md` (wave 2). The first measured a 2026-07-03 snapshot of the skill body: 3/3 vs 0/7 pooled controls, p = 0.0083. The re-run refreshed the inject asset from the **worktree** (engineering-discipline 0.4.0 on merged `main`) and reproduced it criterion-for-criterion: 3/3 vs 0/8 pooled controls on `uv` and `ruff-single-quote`, p = 0.0061, at ~38% fewer tokens than the snapshot body. Covers 1 of the 5 skills the item names. The `humble-vs-super` banks vendor humblepowers 0.4.0 / engineering-discipline 0.1.2 / session-workflow 0.2.2 against merged 0.9.0 / 0.4.0 / 0.21.0 — a re-run there is ~$120 at published power (~$24 for a 1-repeat pilot) and was **not** bought. |
| **CRAF-B21** (retire the always-on injected prose) | **confirmed as far as it goes — but the item's phrasing overstates it** | `docs/reports/2026-07-23-inject-content-v1-findings.md`. Injecting the generic protocol did not beat injecting nothing (9/10 vs 9/10, difference zero, and it was not more expensive). That supports retiring for want of demonstrated benefit. It does **not** show no effect: the interval on the difference spans about ±30 pp, the bank ceilings with bare already at 90%, and the arm that swept (10/10) is itself an injected surface. |
| **KEEL-B09** (pre-mortem directive ablation) | **measured on the structural axis — arm B matches arm A, and the item's own rule fires there; the finding-quality axis remains unmeasured** | `docs/reports/2026-08-11-premortem-ablation-v1-first-matrix.md`. The bank now exists (`tasks/premortem-ablation-v1`, 6 dev + 2 sealed specs from sibling repos, 12 deterministic criteria, `validate` 16 pass / 0 fail). 18 trials, $20.13: the ~500-word core is **identical** to the full 2,429-word body on all nine shared-ask and citation-grounding criteria and loses **only** the three conventions it was never told to emit (p = 0.0022 each), at 80% of the cost, 74% of the tokens and 77% of the wall-clock. `bare` fails 11 of 12, so the directive's value is in being asked at all. **Do not retire on this alone:** whether a finding is an adjudicated real BLOCKER, and the false-positive rate, are the half assigned to a blinded human pass, which is unrun. Repeats 2–3 (~$60) were over the wave's rail and were recorded rather than bought. |
| **MANT-B36** (multi-substrate research vs single-provider) | **still-unmeasured — now with a validated bank and two named blockers instead of a plan** | `docs/reports/2026-08-11-research-fusion-v1-bank-and-precondition-probe.md`. `tasks/research-fusion-v1` exists and validates (8 pass / 0 fail; 11 criteria; 3 dev + 1 sealed **contested** questions, chosen so a fan-out has something to disagree about — a factual set would ceiling and manufacture the null the retirement wants). It measures the moat's **precondition**, not its decision value, because a verifier cannot observe a counterfactual and the post-hoc-answerable question set still does not exist. Two blockers the cost plan did not have: (a) this is the repo's first **MCP-serving** mount, so the vendored tree needs an environment materialised inside `tasks/` at spawn time; (b) the tool's agent-facing result is a bounded projection carrying `divergences` but **not** `sources` / `question` / `generated_at`, so half the criteria need the arm to read the on-disk artifact. The second-provider spend remains invisible to `cost_usd_est`, confirmed. **A direct probe of the tool moved the binding constraint from cost to wall-clock:** one `fast` three-substrate run fanned out in ~3 minutes and then did not finish its synthesis stage inside 50 minutes, so a 60-trial armed arm is over a day sequential and needs a `trial_timeout_s` beyond anything in this corpus. |
| **CONV-B28** (measure convoy's own skill) | **still-unmeasured, and not fathom's to run alone** | It gates on the collection's CRAF-B29, not on a fathom row; the recall half is meant to be imported from CRAF-B29's sealed holdout rather than re-purchased here. (CONV-B17 is a CLI argument-name bug with no measurement — it does not belong in this list.) |

**The one thing that cannot be re-measured.** The unarmed-arm run that motivated FATH-B01 is
unrecoverable: `tasks/serena-nav-v1/` and `-v2/` hold no bank and no ledger. The instrument is fixed
and the experiment is gone, so "did the arming defect change that verdict?" is now permanently
unanswerable. That is FATH-B20, and it is the strongest argument in this file for closing it.

**The two 0/180 banks were not re-run, deliberately.** `humble-vs-super-v3` and `-v4` both pass
validation now (3 pass / 0 fail and 2 pass / 0 fail): their fixtures do leave work for an arm. Their
ceiling was the *other* mode — tasks too easy, so every arm succeeds — which the triad explicitly
cannot detect and which a re-run would simply reproduce at full price. Re-running them would buy a
known answer.

## Reconciled — shipped since the last sweep, not re-proposed

- `[settings] inject`, the user-scope hook arming axis (`1d6de89`). Its two follow-ups did not ship and
  are folded into FATH-B01 and FATH-B10.
- Opt-in raw-stream persistence: `FATHOM_STREAM_DIR` plus per-trial `FATHOM_STREAM_TAG` (`b4bad23`).
- Calibration arm→tier resolution by model-family token with a per-bank `[arms]` override (`9be97e5`),
  with the two-pass run-attribution cost fix (`5aa236f`) and cost-anomaly warnings (`28e15a8`).
- The recalibration playbook's Step 0 repointed at the single model-policy owner (`495b5dc`).
- A plan of record for the tier-separating, oracle-crossed bank: the 2026-07-14 design spec plus
  ADR-0008 (`5be27e1`, revised `10433ea`). Authoring only — the paid run stays a budget decision.
- Partially: two literal ruff exclusions for vendored trees (`f9ca262`, `d0b2309`). The cause is
  unbound and carried forward as FATH-B15.

Everything else from the corpus was re-confirmed absent in the tree, including several rows that have
been open since the first triage pass.

---

## Now

[SHIPPED 2026-08-11] **FATH-B01 — An arm's arming is asserted, never verified, so an entirely unarmed arm can score 100%.**
*(M · [triage] T9a, reinforced by [review])*

- **Cause / evidence:** fathom validates declarations — the inject file exists, the mount dir is
  non-empty — and stops there. Nothing checks that the treatment reached the spawn and functioned.
  `2026-07-25-serena-nav-arming-defect` (BLOCKER): a plugin-mounted server's tools are named
  `mcp__plugin_<plugin>_<server>__<tool>`, the allow-list said `mcp__serena`, and all 23 tools were
  denied for all 9 armed trials — `smoke` 8/8, plan clean, 18/18 completed, `Infra Errors: 0`,
  scorecard `serena 9/9 (100%)`. About $2.68 of armed-arm spend bought no signal, and
  `ledger/archive/` already held one unarmed-arm invalidation before it.
  `2026-07-11-dc-granularity-ab#2` proposed exactly this probe and was held pending corroboration; the
  predicted failure then happened at a price. `2026-07-24-rtk-graphify-tool-eval` §Friction: `[env]`
  and `[settings]` are unverified by smoke, so a marker probe was hand-written before the paid arm was
  trusted. The review reaches the same place from the other side: the smoke gate is valuable precisely
  because it asserts on real spawns what the stubbed suite cannot, and it has no check group for these
  axes.
- **Change:** for any scenario declaring `[plugins] mount`, `[settings]` or `[env]`, spawn one short
  session with that scenario's own mount and allow-list and assert the treatment is live — an `mcp__*`
  `tool_use` with no permission-denied result, the injected hook firing, the env var visible — refusing
  the run otherwise, with `--force` to override. Home: a new `smoke.py` check group plus a per-scenario
  precondition in `cli.py`'s run path. The stream event-counting this needs already exists in-tree as
  experiment-local code (`scripts-rg2x2/activation_report.py`); lift it into a packaged helper shared
  with FATH-B05, so this is an extraction rather than new parsing.
- **Cross-review — four sibling backlogs are downstream of this row.** The craft collection's CRAF-B01,
  keel's KEEL-B09, convoy's CONV-B28 and mantis-research's MANT-B36 each gate their largest retirement
  decision on a measurement this harness will execute. That changes the stake: an unarmed arm scoring
  100% does not only waste fathom's own spend, it retires a sibling's shipped surface on a null result
  the instrument manufactured. The ordering here was already right; the downstream dependency is the
  part that was not written down, and it is the argument that keeps this first when something cheaper
  looks more urgent. FATH-B02 is the other half of the same precondition.

[SHIPPED 2026-08-11] **FATH-B02 — The rule that decides whether a bank can measure anything is a paragraph, and it has
already failed twice at real cost.** *(M · [review] + [triage] T13c + [research])*

- **Cause / evidence:** CONTRIBUTING states the validation triad in prose — the verifier must fail on
  the unmodified fixture, pass on a reference solution, and the task's gate must run green on the
  fixture. It is simultaneously the guard against the circular-eval trap and the answer to "does the
  bare arm ever actually fail?". Both failure modes have bitten: `ablation-v1` was quality-null by
  instrument (greenfield left no regression surface), and the v3 and v4 harder banks both ceilinged
  with 0/180 correctness failures at n=45 — discovered after the spend, not before it. The landscape
  brief names the same two questions as the ones a reviewer should ask of any harness. A rule that
  must always hold belongs in a gate.
- **Change:** `fathom validate <bank>` asserting the three properties; wire it into CI on any
  `tasks/**` change and into `fathom run` as a pre-flight before the first paid spawn.
- **Triage and review disagree on form, and both are half right.** The triage promotes this knowledge
  as prose (T13c, a bank check-ready checklist in the authoring reference); the review wants a command
  and a CI gate. Split it: the fixture triad is mechanically checkable and belongs in the command; the
  discrimination ratio, the measured turn budget and the discriminate-by-scale judgement are authoring
  judgement and stay in the reference (FATH-B10), which points at the command.
- **Cross-review — the same four backlogs are downstream of this row too.** CRAF-B01, KEEL-B09, CONV-B28
  and MANT-B36 will each be decided by a bank run here. A bank that cannot discriminate returns a null
  that reads as "the tool does not help", and a null is the outcome those four are looking for, so the
  instrument's failure mode and the decision's preferred answer point the same way. With FATH-B01 this
  is their precondition; neither should be traded against a cheaper row.

[SHIPPED 2026-08-11] **FATH-B03 — A trial that never ran emits a full criteria dict, so un-run trials read as real
negatives.** *(S · [triage] T12b)*

- **Cause / evidence:** `verifier_results` is written whenever `trial_result.scored` is true, which is
  every status except `INFRASTRUCTURE`. `2026-07-25-dispatch-phase2-subagent-arms#2`: 166 usage-limit
  casualties landed as `status="errored"` carrying `{correctness: false, footprint: false,
  trigger_reached: false}` — structurally identical to a trial that ran and failed. The first analysis
  pass read them as real negatives and depressed every affected arm's rate on a paid analysis, until it
  was caught by hand. Correctness currently depends on every reader independently remembering to filter
  on `status`.
- **Change:** omit `verifier_results` when `status != "completed"`, or carry an explicit
  `valid: false`. Additive and append-only-safe. It converts a discipline every consumer must remember
  into a property the data cannot violate. Pairs with FATH-B09, which gives budget exhaustion its own
  status so the distinction survives into the report.

**FATH-B04 — The rails guard per-spawn cost while credential lifetime and total spend are what actually
end runs.** *(M · [triage] T11a/T11b + [review])*

- **Cause / evidence:** `2026-07-25-dispatch-phase2-subagent-arms#1` records the third and fourth
  occurrence in a single day — a roughly 4-hour matrix launched on about 48 minutes of token life (227
  trials lost), then a roughly 7-hour matrix launched on about 5 hours (106 lost). Both were
  predictable at launch from data the tool holds. The same report shows a launch-time check alone is
  insufficient: a network stall stretched a 2-hour block to 6 hours (13 trials in 6 hours against a
  10-minute `trial_timeout_s`). `#3` and §Vacuous: `--max-budget-usd` is a per-spawn cap whose help
  text calls itself "the real cost guard for a paid matrix" — a 1116-trial matrix at `$1.00` has a
  $1116 ceiling, and total spend was in fact controlled by hand-splitting the matrix.
  `2026-07-24-e1-outcome-run#1` and `2026-07-11-tu-grounding-v1-first-real-run#3`: the dry-run ceiling
  is `num_planned × $2.00` flat (`cli.py:19`, `cli.py:175`) and ignores the cap in force, so it
  over-warns by 4–25× against observed actuals of roughly $0.08–0.59 per trial and trains the operator
  to ignore it. Ancestors `2026-07-12-dc-stack-v1#2` and `2026-06-14-humble-vs-super-run#2` were
  promoted as a warn a pass ago and never built.
- **Change:** (a) refuse to start when remaining credential life is under estimated matrix duration ×
  margin, and re-check between trials, halting cleanly — a mid-run halt costs nothing because dedupe
  already makes resume free; `--force` overrides. First confirm whether the per-spawn temp
  `CLAUDE_CONFIG_DIR` discards a token the CLI refreshed inside the spawn (`make_isolated_config` plus
  `cleanup_dir`); if it does, copy-config-once-per-run or write-back is the durable half of the fix.
  (b) add `--max-run-usd` halting on cumulative `cost_usd_est`, correct `--max-budget-usd`'s help text
  to "per-spawn cap", and compute the dry-run ceiling from the cap in force.
- **Triage and review disagree on shape.** The review asks for a launch-time TTL pre-flight and a
  per-strategy recalibration of the flat ceiling from the committed ledger; the triage asks for a
  continuous gate and a ceiling derived from the cap in force. Take the triage's continuous form — the
  stall already falsified launch-time-only — and take the review's empirical per-strategy figure as the
  default the ceiling uses when no cap is set, printed with its provenance.

[SHIPPED 2026-08-11 (core; MCP-invocation count deferred)] **FATH-B05 — The scorecard renders point estimates it already has the data to qualify, and verdicts
have flipped as a result.** *(M · [triage] T10a/T10c)*

- **Cause / evidence:** spread, per-cell N, truncation and arming tells all sit in the ledger or one
  stream-parse away, and none reach the page. `report.py` contains no `median`/`stdev`/`spread`/
  `saturat`/`truncat` token anywhere. `2026-07-24-rtk-graphify-tool-eval#2` and §Misses: the Economy
  table's per-arm mean misled the direction on 3 of 5 banks, and the ledger was hand-parsed per trial
  on all four runs to recover the real signal (one bimodal control arm, one single blow-up run).
  `2026-07-25-serena-nav-v2-scale-run#1`: the same means reversed sign between n=2 and n=3 and the
  Pareto star moved with them, on the same arms and bank. `#2`: an arm's mean turns (41.1) exceeded the
  task's `max_turns` (40) with nothing marking it — an arm sitting at the cap has a pass rate that is a
  lower bound, not a score. `2026-07-25-serena-nav-arming-defect#4`: the scorecard held the arming tell
  (+17.6% cache tokens, +1.2 turns, zero successful MCP calls) and drew no attention to it.
- **Change:** render per-arm spread (min/median/max, or IQR) and per-cell N beside every mean in
  Economy and Efficiency; suppress or asterisk the Pareto flag when arms' spreads overlap; add a
  per-arm health line carrying trials at or over `max_turns` / `trial_timeout_s` and, for an arm
  declaring a mount, the count of successful `mcp__*` invocations — flagging "registered but denied"
  when a large cache-token delta meets zero MCP calls. Home: `report.py`, plus turn accounting in the
  adapter for the cap tell, reading the same packaged stream helper FATH-B01 extracts.

[SHIPPED 2026-08-11 (write-ups; warn + CI gate deferred)] **FATH-B06 — A committed ledger with no report is invisible, and five analyses are already in that
state.** *(M · [triage] T2a + [review] + [research])*

- **Cause / evidence:** 14 reports against 19 committed ledgers. STATUS itself marks five analyses
  "Unreported — no `docs/reports/` entry" (`tu-grounding-v1`, `tu-grounding-e2e-v1`,
  `inject-content-v1`, and the three `e1-*` banks), plus the whole rg-2x2 re-run; their conclusions
  survive only in commit messages and another repo's design docs. The failure is structural, not
  personal: the expensive step (running the matrix) is instrumented, resumable and gated, while the
  cheap, decisive step (writing the verdict where a consumer can find it) is unenforced prose. The
  prose form shipped in CONTRIBUTING and recurred; the escalation to a mechanical check has been
  written down as cleared-for-build since the first triage pass and is still unbuilt. Operator
  observation reports downstream tools sitting unmeasured while waiting on fathom verdicts — the
  bank gets built and run, and the verdict never reaches a consumer.
- **Change:** `fathom report` warns when a bank's ledger has no matching `docs/reports/` entry and no
  STATUS row; CI fails when a newly committed ledger lacks both; add a minimal report template so
  closing an analysis is a rendering plus a paragraph rather than an essay. Then close the five open
  ones — the ledgers exist, so none of them needs a re-run.
- **Triage and review differ by one rung:** the triage row stops at the warn, the review adds the CI
  failure. Ship both — the warn helps the operator in the moment, the CI gate is the part that binds.
- **Cross-review — write up first the analyses a sibling backlog already treats as settled.** The five
  are not equally urgent. `inject-content-v1` is the analysis CRAF-B21 cites to justify retiring an
  always-on surface, and the three `e1-*` banks are the pre-registered discipline trials the collection's
  routed-out section quotes by number. So a backlog next door is retiring a shipped surface, and
  declining work, on evidence this backlog classifies as unpublished — the conclusion is load-bearing
  somewhere while being unfindable here. Order the write-ups accordingly: `inject-content-v1` first,
  then the `e1-*` trials, then the rest. None needs a re-run, and each closes a live dependency rather
  than tidying the index.

**FATH-B51 — The ledger undercounts economy on the delegated path, and the published ×3.81 correction
is refuted as stated, so every delegated cost figure is a floor of unknown depth.**
*(M · [verif-lift closure])*

- **Cause / evidence:** on the delegated path the ledger records the parent's final iteration and omits
  the subagent's consumption outright. `verif-lift-trunc-v1` `bare` runs average **1.0 turns, 331 output
  tokens and 5.7 s** while scoring 10/10 on `spec_met` for a code-fix task — work that cannot have been
  done in 331 parent tokens. The undercount is therefore real. **Its published explanation is not.** The
  ×3.81 multiplier was justified as: every arm delegates, so each stream carries two `result` events
  (parent + subagent sidechain), and `parse_stream` keeps the last. Measured against the **1,072** saved
  streams, that mechanism fails three ways: all 15 opus streams delegate (`Agent` tool 15/15) and each
  carries **exactly one** `result` event; across the 959 plugin-mounted streams the second event tracks
  the **stop hook**, not the subagent (fired + 2nd: 164; silent + 1st: 794; silent + 2nd: 1; fired +
  1st: **0**); and where two events do exist the ratio runs **1.16–2.02, median 1.49**, with **0 of 232**
  reaching 3.81. So ×3.81 cannot have come from this mechanism on any stream in the corpus. The cost of
  leaving it: a per-program budget ceiling is computed from ledger sums, and the grid this wave priced
  came to ≈$94 in floor units against ≈$223 corrected — the difference between fitting a $120 ceiling
  and overrunning it by 86%.
- **Change:** re-derive the delegated-path correction from the actual mechanism — sum the subagent
  sidechain's usage into the trial's economy at parse time rather than post-hoc multiplying — and make
  `parse_stream` state which events it folded, so the figure is auditable instead of asserted. Until it
  is re-derived: **keep ×3.81 as the budgeting unit** (it over-reserves rather than overspends, so it is
  conservative in the safe direction) and **stop publishing it as a measured multiplier**. Report every
  delegated economy figure as a floor, and make no arm-to-arm economy claim from these figures at all —
  the bias is not guaranteed common-mode across arms.
- **Gate:** independent of the matrix; it is instrument work on saved streams and costs no spawns.
  Pairs with FATH-B01's arming verification, which is the same class of defect — a declared property of a
  run that nothing checks.

---

## Next

**FATH-B07 — The ledger is a public contract with no written contract.** *(S · [triage] T12a)*

- **Cause / evidence:** it is read by `report.py`, `calibration.py` and two external consumers.
  `2026-07-24-experiment-rigor-bridge-design#1`: a consumer written from memory keyed on a `type` field
  that does not exist and read `cost_usd` instead of `cost_usd_est` — a reader of a fictional ledger,
  caught only when a reviewer opened the real file. `2026-07-25-serena-nav-arming-defect#5`: a second
  fresh consumer guessed `tokens_total` / `usd_est` / `wall_s` and got `None` for every one.
  `2026-07-24-e1-outcome-run#4` and `2026-07-24-rtk-graphify-tool-eval#3`: the trial→run join was
  hand-rolled twice in one report and three times in another.
- **Change:** one page carrying the `kind` discriminator, the run and trial field lists, the trial→run
  join key `(bank, task_id, repeat, config_hash)` with "one trial may have several run rows",
  per-experiment cost as the sum of run-row `cost_usd_est`, and the infra-exclusion rule for pass-rate
  denominators; a docstring-of-record on the ledger writer; and a decision on `_is_pass` — export it as
  `fathom.report.is_pass` or state a stability promise, since it is already vendored byte-identical
  downstream.

**FATH-B08 — The anti-ceiling metric renders only for calibration banks, so most scorecards lead with
an all-truthy headline.** *(M · [triage] T1a/T10b + [review])*

- **Cause / evidence:** `report.py:512` still gates the hard-criteria quality fraction on a bank
  shipping `scores.toml`, so the banks most at risk of saturation show the least informative headline.
  Saturation itself is a known limitation living in playbook prose: `2026-07-14-model-selection-
  design#6` and §Misses, reinforced by `2026-07-24-rtk-graphify-tool-eval` §Misses — a design consumer
  built a proposal on a saturated bank and a blind reviewer, not the scorecard, caught it. This row has
  been open since the first triage pass.
- **Change:** promote the hard-criteria fraction from `calibration.py` into the core report for all
  banks; when every arm passes at least K of N tasks, print a saturation banner on the scorecard and
  point the reader at the economy axis, which FATH-B05 must first make trustworthy.

**FATH-B09 — Errored and truncated trials are excluded from the per-criterion table, hiding real
partial-compliance data.** *(S · [review] + STATUS open defect)*

- **Cause / evidence:** a max-turns or timeout truncation drops the trial out of the per-criterion
  table entirely, so the signal is visible only by reading the ledger directly. STATUS has carried this
  as an open reporting defect since the 2026-07-05 audit. The same audit recorded `infra_error` as a
  phantom field that `report.py` and `calibration.py` both guard and no producer ever writes.
- **Change:** split budget exhaustion from task error as a distinct `TrialStatus`
  (`strategies/base.py`) and include it in the per-criterion table; delete the `infra_error` field and
  its guards, accepting the ripple into the "Infra Errors" column and the golden file. Pairs with
  FATH-B03.

**FATH-B10 — Proven authoring recipes and their traps live only in the feedback corpus, so every
campaign re-derives them and one of them pays.** *(M · [triage] T13a–T13f)*

- **Cause / evidence:** unchanged cause from two triage passes ago (T7, T8, both unbuilt), now with six
  more occurrences. `2026-07-25-serena-nav-arming-defect#2`: the MCP tool-naming rule is unguessable
  and self-contradictory across observable spellings — tools are `mcp__plugin_<plugin>_<server>__<tool>`
  while the init event names the server `plugin:<plugin>:<server>`, so even copying the init-event name
  into the allow-list fails. `2026-07-24-rtk-graphify-tool-eval#1(b)`: plugin hooks do not fire in
  headless `-p`, only user-scope settings hooks do — a one-line doctrine note would have saved a
  mid-eval dead end and the harness change that followed. `#4`: the real-repo-with-third-party-deps
  pattern (verifier shells to a host interpreter carrying the deps, the arm gets the same interpreter
  via `[env] PATH`), derived by trial against an environment-scoped internal tool's subtree.
  `2026-07-25-serena-nav-arming-defect#6`, `2026-07-25-serena-nav-v2-scale-run#3` and
  `2026-07-24-rtk-graphify-tool-eval` §Misses: discrimination comes from corpus scale and turn budget,
  not task cleverness — 34 files ceilinged despite deliberate decoys, 422 files separated cleanly.
  `2026-07-25-serena-nav-v2-scale-run#4`: `truth.json` beside `verify.py` is a sanctioned ground-truth
  pattern with a non-obvious safety property (only `fixtures/` is staged, so the key is unreachable).
  `#5` and `2026-07-25-serena-nav-arming-defect#3`: `--limit N` is scenario-major, so a `--limit 6`
  pilot on a two-arm matrix spends all six on the anchor arm and never reaches the risky one.
  `2026-07-24-e1-outcome-run#3` and `2026-07-24-rg2x2-stream-instrumentation#3`: two operator notes
  with no home — the Windows worktree MAX_PATH workaround and a stream-dir hygiene policy.
- **Change:** split `reference/authoring.md` (174 lines, schemas only) into `authoring.md` (schemas,
  unchanged), `arming.md` (the MCP-served-arms section and the arming-axis doctrine table: which axis
  fires where, and how each is verified) and `bank-design.md` (the check-ready checklist and the
  fixture patterns) **before** the additions land, and displace the duplicated abridged schema in
  `CLAUDE.md` with a pointer. Operator notes go beside the rails they qualify in the skill's cost
  section.
- **Two homing corrections.** The bank discrimination pre-check is homed by two reports in
  `docs/method/definition-of-ready.md`, but that DoR governs fathom's own build specs — the authoring
  reference is the right home. And T13c's proposed pointer from `docs/method/review-checklist.md` needs
  a new target if FATH-B37 deletes that file; point at the upstream original or directly at
  `bank-design.md`.
- **Cross-review — give the two new files a budget at birth.** `arming.md` and `bank-design.md` are
  being created to absorb six-plus findings with no stated cap, which is exactly how the surface
  FATH-B21 is now trimming came to be: each addition was individually justified and nothing ever had to
  name what it displaced. Set a line budget for each file in its own header at creation, and make an
  addition that would exceed it either displace something or argue for a raised budget. A new reference
  file with no ratchet is the next surface that only grows, and this pass is the cheapest moment to
  attach one.

**FATH-B11 — Environment identity is asserted at declaration time, not fingerprinted at execution
time.** *(M · [triage] T9b + [research])*

- **Cause / evidence:** `2026-07-12-dc-v4-design` §Misses and `#2`: a mounted server was silently
  stale — a path-dependency wheel cache served pre-v4 code under a bumped `dataset_version`, caught
  only by an ad-hoc executed probe. `#1`, extending `2026-07-01-recalibration-usefulness#3`: new server
  code behind a `file://` mount forks neither `config_hash` nor the resume key, so an unbumped re-run
  resume-skips and reports the old payloads' scores as if they measured the new ones. The same property
  answers the landscape brief's sharpest question of any harness — whether it can distinguish scorer
  drift from subject drift.
- **Change:** record the resolved package version or source hash of a path-dependency server at run
  start and refuse-or-warn when it changed while `dataset_version` and `config_hash` did not. Fold in
  the long-open watch row for the mirror case — task content (instruction, `verify.py`, fixtures)
  changing without a `dataset_version` bump.

**FATH-B12 — The smoke gate can pass hollow, which is the failure mode the harness exists to detect
elsewhere.** *(S · [triage] T3a/T3b + [review])*

- **Cause / evidence:** STATUS names it: some checks are satisfied by absence, so the gate can pass
  under an expired credential. A gate that can pass by absence is vacuous. Two adjacent defects have
  been open since the first triage pass: no forced UTF-8 on harness stdout (a spawn emitting a
  non-cp1252 character crashes the print on a Windows console; no `reconfigure` call exists anywhere in
  `src/`), and `smoke` does not plumb `--effort`/`--model`, which blocks an effort-acceptance probe
  before a paid effort run.
- **Change:** fail fast as INFRA-BLOCKED on an infrastructure-classified check rather than letting
  absence satisfy it; `reconfigure(errors="replace")` on stdout in `smoke.py` and `cli.py`; plumb
  `--effort`/`--model` through the smoke subparser.
- **Cross-review — the encoding half is already solved next door; cite it rather than re-deriving it.**
  convoy shipped UTF-8 pinning at every text boundary in PR #11 — regression tests plus the entry-point
  streams, not a single call site — and the warning has not recurred in any later feedback report. Take
  that as the reference implementation for the `reconfigure` work here. The shape worth copying is the
  boundary sweep: the collection now has a third instance of the same defect, a lint that dies printing
  to a cp1252 stdout, which is what a per-call-site fix leaves behind.

**FATH-B13 — A run prints two plan lines and then nothing, and per-trial economy is a hand-join.**
*(M · [triage] T4a/T4b/T12c)*

- **Cause / evidence:** `cli.py` emits the plan and then stays silent until exit, so a multi-hour
  matrix gives no progress signal and headless captures must read the ledger to learn what a run cost.
  Per-trial economy is the single most-asked question of the ledger and was hand-joined in three
  separate reports (`2026-07-24-e1-outcome-run#4`, `2026-07-24-rtk-graphify-tool-eval#3`, and again in
  the dispatch-phase2 analysis).
- **Change:** one flushed progress line per trial; a closing summary naming the ledger path, completed
  and skipped counts, and total USD; and either a cost/tokens field on new trial rows or a
  `fathom report --per-trial` view. Both are additive.

[SHIPPED 2026-08-11] **FATH-B14 — Trials destroy their own evidence, and the fix is smaller than the reports proposed.**
*(S · [triage] T5a)*

- **Cause / evidence:** the verifier's parsed answers are discarded, so a failing criterion cannot be
  diagnosed without re-running the trial. Grounding changed the proposal: `VerifierResult` already
  carries `stdout` and it is in hand at the write site (`cli.py:234`) — it is simply dropped. Reported
  twice more this round in `2026-07-12-dc-v4-design` and `2026-07-25-serena-nav-arming-defect#7`.
- **Change:** persist the verifier's parsed answers onto the trial row. The larger proposal (retaining
  the result view on failure) stays held — revisit only if this proves insufficient.

**FATH-B15 — Vendored trees have no conventional home, so each new location re-breaks CI and earns one
more literal.** *(S · [triage] T14a)*

- **Cause / evidence:** `2026-07-24-e1-outcome-run` §CI: `ruff format --check .` swept 52 vendored
  files, fixed by adding a literal. `2026-07-24-rg2x2-stream-instrumentation#2`: it recurred at a third
  location and earned a second literal — the report invokes the escalation rule itself. `pyproject.toml`
  now carries three literals under a comment that counts the occurrences.
- **Change:** bind the cause one rung down — either a single conventional vendoring root matched by one
  pattern (moving the three existing locations into it), or a CI guard that fails naming any
  `plugin.json`-bearing tree outside the excluded set. Prefer the guard: a mounted directory's path is
  part of the arm's identity, so relocation churns committed ledgers' `config_hash` inputs. That
  constraint also bears on FATH-B24, which proposes moving the same trees for a different reason.

**FATH-B16 — Three hand-maintained mirrors of upstream model data live here, none dated, none tested.**
*(M · [review] + operator observation)*

- **Cause / evidence:** the per-family price table in the adapter (`claude_cli.py:297`) and
  `FAMILY_TIERS` plus `THRESHOLDS` in `calibration.py`. All four price rows were checked live against
  the current published lineup and are correct today, so the risk is structural rather than present.
  But the table is undated, has no review-by tripwire and no test; the substring matcher silently
  prices any unrecognized model id at the strong rate, so a new model quietly produces a
  plausible-but-wrong USD figure; and it shadows a canonical file that deliberately carries no prices
  precisely to avoid creating an unowned mirror. Separately, the recalibration playbook has a stated
  trigger ("a new model ships, or quarterly") that nothing fires, because the trigger lives in a
  different repo from its owner.
- **Change:** consolidate the three into one dated data file with `reviewed_on` / `review_by`, read by
  both `calibration.py` and the adapter, with a test that fails once the horizon passes; record
  `cost_usd_est` as null and warn on an unrecognized model id instead of applying the strong rate;
  register the file wherever the stack's other model mirrors are walked on a launch; and move the
  recalibration trigger and ownership row to the model-policy owner while the procedure stays here.
  Keep tokens and turns as the primary economy currency — the Sonnet-costs-more-than-Opus surprise in
  STATUS is explained entirely by token count, not by a wrong rate.
- **Cross-review — retire the price half rather than dating it.** The item above assumes a USD figure
  has to be estimated from a local table, so the table needs a `review_by` and a test. convoy measured
  otherwise: across 76 production spawns, and in a direct check against the same installed CLI on a
  subscription seat, the terminal result event carries a real `total_cost_usd` rather than `0.0`. That
  falsifies the estimate-from-a-table premise this table shares with the one convoy is deleting on the
  same finding (CONV-B29). If the cost is reported per spawn, the per-family price table is not a mirror
  to be dated but a mirror to be removed: read the reported figure into `cost_usd_est`, keep tokens and
  turns as the primary currency exactly as this item already argues, and let the tier half
  (`FAMILY_TIERS`, `THRESHOLDS`) consolidate on its own — a smaller change than the dated data file, and
  one that removes rather than schedules the drift. Confirm the field on this repo's own adapter path
  before deleting anything; if it does not reproduce here, the standing argument above holds unchanged.

**FATH-B17 — Run the deciding measurement for the series strategy.** *(M · [review] + [research])*

- **Cause / evidence:** it is the most expensive feature in the harness by every measure — the largest
  strategy at 606 lines, the one sanctioned non-adapter model call, a 3600s trial timeout, a whole
  smoke check group, an engine-agnostic contract spec and a `[tools] source="repo"` code path —
  supported by one scenario file and one analysis: six trials on 2026-06-10 whose verdict was no
  quality gain at ~4.6× tokens and 8 sessions per trial. The ablation-v2 engine arm is recorded as not
  run; the usefulness study then found bare Sonnet 5 one-shots the probe tasks, moving the coordination
  threshold up. It has also caused one real outage (the 2026-07-05 relative-path regression dropped
  smoke to 7/8). The landscape brief sharpens what is actually left to test: native subagents, agent
  teams and worktree isolation have absorbed mechanical fan-out, and the residue is dependency-ordered
  execution under per-phase budgets with gates that can reject "done".
- **Change:** run the engine arm against ablation-v2's brownfield instrument at the weak tier — the one
  configuration in the corpus where the bare arm actually fails (8/8 gates green, 5/8 oracle escapes)
  and an orchestration engine therefore has escapes to catch. The bank, arms and oracle already exist
  and the real cost is near zero under subscription auth. If it does not beat the gated weak-tier arm,
  FATH-B36 retires the strategy, the contract spec and the smoke group together.
- **Cross-review — fold in the non-experimental evidence convoy already holds.** The verdict as written
  rests on one weak-tier arm against one bank, which is thin for a decision that retires a strategy, a
  contract spec and a smoke group. convoy has direct evidence on the same residual claim from production
  series rather than a bank: a "done" claim was rejected 5 times across 73 gate events, with every red
  either repaired or halted rather than passed through; per-role budget caps halted 2 of 10 terminal
  runs; and the independent lane fired red 0 times in 14 firings. That is the dependency-ordered-
  execution-under-budgets-with-gates-that-can-reject-done claim being exercised at cost outside this
  repo. Cite it beside the ablation-v2 arm, and let it sharpen what the arm has to add: not whether
  gates fire at all, but whether the engine catches escapes the bare arm misses. The 0-of-14
  independent-lane figure cuts the other way and belongs in the verdict too.

**FATH-B18 — The schema has no notion of a factor, so factorial experiments smuggle theirs into task-id
suffixes.** *(M · [triage] T15a + [research])*

- **Cause / evidence:** `2026-07-24-inject-content-ab#2`: the register variable lived in task-id
  suffixes and the report pools them, so the arm × register table was hand-rolled from the ledger.
  `2026-07-24-e1-outcome-run` §Friction: `[context] inject` is per-scenario, so a per-task-precise hint
  is impossible in one bank — worked around by splitting into three per-discipline banks. The landscape
  brief independently names factorial design over scaffold configurations as the sharpest adjacent
  instrument in this space, which is the same abstraction.
- **Change:** bank-declared task tags (`[tags]` in `task.toml`, or a bank-level factor map) with
  per-tag grouping in the scorecard, so a factorial's split needs no hand-rolled ledger pass. The same
  tag can later carry a per-task inject override.

**FATH-B19 — `fathom report` accepts none of the directory flags `fathom run` requires.** *(S ·
[triage] v1 rows + [review])*

- **Cause / evidence:** `report` reads `tasks/<bank>/` and `ledger/<bank>.jsonl` unconditionally while
  `run` takes `--scenarios-dir` / `--tasks-dir` / `--ledger-dir`, so a calibration bank run from an
  alternate tasks dir renders a scorecard with the whole Calibration section silently missing. Open
  since the first triage pass and currently documented as a limitation rather than fixed.
- **Change:** thread the three flags through `report`, or emit an explicit warning on the asymmetry.

**FATH-B20 — One analysis has a surviving conclusion and no recoverable evidence.** *(S · [review])*

- **Cause / evidence:** `tasks/serena-nav-v1/` and `tasks/serena-nav-v2/` contain only stale
  `__pycache__` `.pyc` files — zero non-pyc files, which is why `git status` reads clean — while
  `report/scorecard-serena-nav-v2.md` still holds a full rendered verdict (9/9 vs 8/9, with
  per-criterion detail) whose ledger exists nowhere in the repo and which appears in no STATUS row.
  Meanwhile the two serena-nav feedback reports are among the most load-bearing evidence in this
  backlog. In a repo whose central discipline is an append-only evidence record, this is the one
  artifact that must not exist.
- **Change:** restore the bank and ledger from wherever they were run and add a STATUS row, or delete
  the empty directories and the orphaned scorecard. Either is acceptable; leaving it is not.

**FATH-B47 — Every trial gets exactly one user prompt, so any multi-turn question is unaskable.** *(M ·
[triage] T15b + [cross-review])*

- **Cause / evidence:** promoted out of FATH-B31's watch list. The adapter spawns one headless session
  per trial and tears the config dir down with it, so a scenario cannot script a second prompt. T15b
  recorded the first experiment blocked by this. The cross-review supplies the second: the collection
  routed its cadence and salience-decay arms here explicitly, and both are questions about what happens
  on a later prompt, which a one-prompt instrument cannot pose at all. Two independent blocked
  experiments is the bar this row was held against.
- **Change:** a per-trial config-dir lifecycle that survives more than one spawn, a continue-session
  spawn mode on the adapter, and a `prompts = [...]` strategy that walks them in order. Scope it to the
  smallest thing that unblocks a two-prompt arm; the cadence and decay designs can then be authored
  against a real instrument instead of waiting on one. FATH-B18's task tags are the natural carrier if
  the prompt sequence needs to vary per task.

### Wave-3 field defects (2026-08-12)

Seven instrument defects the 2026-08-12 measurement waves hit while trying to spend. They sit at the
end of **Next** rather than in **Later** because each has an observed price attached this week, not an
argued one. Three already have a home and are recorded here as pointers rather than as second rows —
duplicating a row is how a backlog stops being the backlog of record:

- **Economy pooled by arm name across `config_hash`es** — **FATH-B49**, extended above with the
  general statement (a re-run against changed injected content is the shape that fires it) and the
  rule that follows from it (key on the hash; render the name as a label).
- **The delegated path undercounts economy** — **FATH-B51**, arriving with the `verif-lift` closure
  branch, which measured it against the saved streams. The finding to carry forward, because it is
  the part that is easiest to lose in transit: the undercount is **real** — a trial that delegates
  through the Task tool records only the parent's final iteration, and the subagent's consumption is
  absent from the ledger entirely — but the mechanism first proposed for it (two `result` events per
  stream, `parse_stream` keeping the last) **does not reproduce**. Measured on the saved streams, a
  second `result` appears only where a stop hook adds a turn, at **1.00–1.44×**, nowhere near the
  **×3.81** correction in use. So the undercount is real by a route not yet identified, and ×3.81 is
  usable **only as a conservative budgeting unit** — it over-reserves rather than overspends — and
  **must not be published as a measured multiplier**. The ID is reserved here so it is not reused
  before that branch lands.
- **`--max-budget-usd` is a per-spawn cap, not a matrix total** — **FATH-B04**, whose (b) already
  names it and whose text a pending branch is amending, so the wave-3 evidence is recorded here
  rather than as a conflicting edit to that row. The arithmetic is the part worth keeping: the flag
  reads as a program rail and is not one, so **an operator intending a $30 program rail licenses
  roughly $1,440 across a 48-trial matrix**. The failure is not that the guard is weak; it is that
  the guard's *name* asserts a guarantee it does not make, which is why operators keep re-deriving it
  one wave at a time. Compounding it, the printed dry-run "ceiling" was the conservative flat
  $2/trial figure, **decoupled from the flag entirely** — so the two numbers an operator reads before
  spending disagreed, and neither bounded the run. Direction: a genuine program-level rail
  (`--max-run-usd`, halting on cumulative `cost_usd_est`) **or** a rename that says what the flag
  does (`--max-spawn-usd`), with the ceiling computed from the cap actually in force. The rename is
  worth shipping even if the rail is not — an honest name costs nothing and removes the whole class.

**FATH-B52 — `verify-arming` reports a correctly armed MCP arm as unarmed, and the way out it pushes
the operator toward is the unsafe one.** *(S · [wave-3 run])*

- **Cause / evidence:** the probe reads the CLI's **init event** and checks each declared server's
  status against `HEALTHY_MCP_STATUSES` (`arming.py`). That event is emitted at session start. A
  stdio MCP server that needs **6–11 s to connect under load** has not connected when the snapshot is
  taken, so the one sample the check looks at shows it unhealthy — and an arm whose server does come
  up, and whose tools the model then really calls, fails the pre-flight and the run refuses with
  `EXIT_UNARMED`. Observed directly this wave: a mount that handshook healthy in 2.4 s and had the
  model genuinely call its tool on 4 of 4 live spawns still read NOT ARMED, and the same probe listed
  the ambient MCP tools on one sampling and `[]` minutes later — the timing dependency stated outright.
- **Why this is worse than a plain gap.** The pre-flight is the last gate before a paid matrix, so a
  false negative presents to the operator as "the instrument refuses to start", with exactly one
  documented remedy: `--skip-arming-check`. The defect's own pressure therefore points at **disabling
  the check FATH-B01 was built to add**, on MCP-served arms — the arms where an unarmed run is
  hardest to notice afterwards. A gate that fails safe costs time; a gate that fails toward its own
  blanket override is a hazard, and it should be priced as one.
- **Change:** stop treating the init event as the whole observation. Take the server's **last-seen**
  status in the probe stream (or a bounded poll) and pass when it ever reached a healthy state,
  keeping the init sample as the fast path. Stronger still, corroborate at the tool level with the
  helper already in tree: `tools_served_by` plus one observed `mcp__*` `tool_use` with no
  permission-denied result settles the question with no timing assumption at all. Whichever form,
  the refusal must name the server and its last-seen status, and must offer a scoped wait
  (`--arming-mcp-timeout S`) **before** it offers the blanket flag.

**FATH-B53 — Nothing in fathom serializes paid runs, so mutual exclusion is an ad-hoc caller
convention — and it deadlocked three times in one day.** *(M · [wave-3 run])*

- **Cause / evidence:** a paid matrix consumes one seat's credential and rate budget, so two
  concurrent runs on the same seat interfere. fathom ships no lock; serialization is delegated
  entirely to whatever convention each caller invents. With several concurrent sessions on one seat
  that produced **three deadlocks in a single day** — **twice** from a holder that had already
  finished spending and never released, and **once** from a process that had died still holding the
  claim. The cost is not the waiting. A session blocked on a phantom holder either stalls a whole
  wave or talks itself into overriding, and **neither is decidable from the artifacts**, because
  nothing in the claim records whether its holder is alive. Two of this wave's programs reached their
  paid window, found the lock held, and bought nothing.
- **Change:** a native lock owned by fathom rather than by its callers. convoy ships the precedent
  (`.git/convoy-run.lock`), so the shape is already argued next door; what it needs here are the two
  properties the ad-hoc conventions lack. **(a) A heartbeat** written by the holder, so staleness is
  decidable from the lock's own timestamps against a stated horizon instead of by guessing at process
  tables — this is the half the three observed deadlocks name directly, since a finished or dead
  holder then expires rather than blocking forever. **(b) A FIFO ticket directory** rather than a
  single flag, so the release-to-relock window stops being a race that the politest poller always
  loses. Home: the run path in `cli.py`, released in a `finally` that survives the Windows
  process-tree teardown this repo already does where it spawns.

**FATH-B54 — A gate command is handed to the shell verbatim with no path validation, so a committed
placeholder silently degraded an armed arm to the ungated one.** *(S · [wave-3 run])*

- **Cause / evidence:** gate commands are strings executed from the workspace cwd, and nothing checks
  that the paths they name exist. A committed scenario shipped
  `python /path/to/fathom/tasks/.../type_probe.py .` — a **literal editing placeholder** that was
  never filled in. The command could not find its script, the gate contributed nothing, and the arm
  ran as the ungated arm under the gated arm's name. It scored **9/10**, and that number is now
  **unattributable**: no preimage of its ledger `config_hash` was found across roughly **170k**
  candidate forms, so it cannot even be established which configuration produced it. This is the
  FATH-B01 / FATH-B50 class reached by a third route — a confident number from an arm that was not
  the arm — and the worst of the three, because it destroys the evidence rather than merely biasing
  it: a biased trial can be re-read, an unattributable one can only be discarded.
- **Change:** validate at **validate time**, before the first paid spawn. For every task's
  `[gate] run` and every scenario's `[gate] extra`, extract the path-shaped tokens and assert each
  resolves under the substitution the arm will actually use, refusing in the class of
  `EXIT_BANK_INVALID`. Home: `fathom validate` (FATH-B02), already the pre-flight in the run path.
  The distinction to encode is small and load-bearing: a gate that **ran and went red** is a
  legitimate result; a gate that **could never have run** is a broken arm and must not reach a spawn.
  The enabling half is in flight on a pending branch — `${task_dir}` / `${workspace}` expansion in
  `gated_session.py` gives a gate command a portable way to name a harness-side path at all, which is
  what turns "does it resolve?" into a checkable question instead of an unanswerable one.

**FATH-B55 — The credential model does not survive a matrix longer than a token, so a long matrix is
only viable chunked and resumable.** *(M · [wave-3 run])*

- **Cause / evidence:** this answers the question FATH-B04 (a) held open, and the answer changes the
  shape of the fix rather than confirming it. Under ADR-0004 every spawn copies the shared OAuth
  credential into a throwaway `CLAUDE_CONFIG_DIR`, the CLI refreshes it **independently inside that
  spawn**, and the refreshed token is discarded with the directory. Two consequences, both
  structural: **(a)** under refresh-token rotation, concurrent spawns redeem the same refresh token
  and invalidate one another — the credential half of the interference FATH-B53 records as deadlocks;
  **(b)** the access token's own lifetime is about **8 hours**, while a matrix at this wave's scale
  runs **longer than a day** of wall clock, so mid-run expiry is the expected path rather than an edge
  case. Observed cost: three separate paid windows across the wave bought nothing, and in two of them
  the attributed cause was an expired session failing `fathom smoke`'s auth checks — with the run
  lock free on the first poll.
- **The operational consequence, which is the part to record.** No pre-flight can fix (b): a
  credential-TTL check at launch is correct, and still correct when the token dies six hours later.
  **A long matrix must therefore be chunked and resumable** — the only run shape that survives a
  mid-run expiry, and nearly free here, because resume already costs nothing (the dedupe key makes a
  re-invocation skip completed trials). Plan in blocks that fit inside a token's life, re-authenticate
  between blocks, and treat "run the whole matrix in one invocation" as the anti-pattern it is.
- **Change:** write the chunking rule into the cost/rails section operators actually read, and make
  the tool support that shape rather than merely tolerate it. The closing summary FATH-B13 proposes —
  trials remaining, and the exact resume command — is most of it; a `--chunk N` that stops cleanly on
  a stated boundary is the rest. The durable fix for (a) is the one FATH-B04 already names: copy the
  config once per run, or write the refreshed credential back, so spawns stop racing each other's
  refresh.

**FATH-B56 — A relative `[tools] repo` resolves against the process cwd, so the series arm points at
nothing outside the canonical checkout and `fathom smoke` reads 7/8.** *(S · [wave-3 run])*

- **Cause / evidence:** `scenarios/series.toml` carries `repo = "../convoy"`, and
  `resolve_repo_invocation_cmd` (`scenario.py`) resolves it with `Path(repo).resolve()` — against
  **fathom's own process cwd**, not against the scenario file that wrote it. In the canonical
  checkout that lands on the sibling engine repo and works. From a git worktree, or any checkout not
  laid out as siblings, it resolves to a path that does not exist, the engine-boundary group cannot
  run, and `fathom smoke` reads **7/8**. Cost: 8/8 is the documented go/no-go before any paid matrix,
  so an operator in a worktree meets a failing gate that says nothing about spawn isolation, and the
  remedy is a layout fact written down nowhere — every wave-3 program working from a worktree
  re-derived it. The class is a repeat: the 2026-07-05 outage this same helper was written to close
  was also a relative repo path that could not resolve from where it was used. The helper fixed the
  cwd at **spawn** time and left the cwd at **resolution** time as the surviving assumption.
- **Change:** resolve a relative `[tools] repo` against the **scenario file's** directory, as
  `[context] inject` and `[settings] inject` already are, so the path means one thing from every cwd.
  If that is judged to move committed `config_hash` inputs — the resolved string enters the hash —
  take the cheaper half instead and **fail loudly**: refuse at resolution time when the resolved repo
  does not exist, naming the path it resolved to, rather than emitting an invocation command that
  cannot run. Either way the worktree case belongs beside the documented 8/8 expectation, which
  `docs/STATUS.md` now states.

---

## Later

**FATH-B21 — `CLAUDE.md` duplicates the on-demand skill on an always-loaded surface.** *(S ·
[review] + [research])*

The four-step run recipe, the cost rails, the four invariants and an abridged scenario schema all
appear in both, with the full schema in the authoring reference. Skill leakage on an always-on surface
is the configuration smell with the strongest empirical support. Cut the run recipe and the abridged
schema block; keep the gate commands, the invariants, the stdlib-core convention, the Windows
path/process-tree note, the never-edit-the-ledger rule, the state pointer, and the instruction not to
gate on an exact test count. Expect roughly a halving with no loss. Rides FATH-B10, which names this
as the displacement its additions pay for.

**FATH-B22 — The sealed-holdout invariant is nominal.** *(S · [review])*

16 of 19 banks ship `holdout = []`, only 3 carry a task, and grepping every committed ledger for
`"holdout": true` returns nothing — the `--include-holdout` path has never been exercised on the
record. A required key satisfiable with an empty list is not a gate, and several banks' arms have been
tuned against their own results. Either make a non-empty `holdout` a validation error for any bank
feeding a tuning loop, or state plainly in ADR-0005 that the invariant covers promotion-decision banks
only and mark the other 16 exploratory. Then run one holdout spend end-to-end so the
marked-and-reported-separately path is proven rather than assumed.

**FATH-B23 — Two ADR citations resolve to the wrong decision.** *(S · [review] + STATUS)*

An ADR-0008 was lost in a July history squash and its number was reused by an unrelated 2026-07-15
decision, so the context-size bank's citations now mis-resolve rather than dangle — a silently wrong
pointer is worse than a missing one. A cited ADR-0009 exists in neither this repo nor the engine repo,
and a cited `docs/concepts.md` was never created. STATUS files both as LOW; the review argues the
collision deserves higher, and that is the right call. De-reference by inlining the decision into the
bank README or re-issue under the next free number; recover or de-reference ADR-0009; and resolve
ADR-0008's own status — a proposal that has sat since 2026-07-15 with its bank unbuilt is a decision
not to do it.

**FATH-B24 — Five near-identical copies of the same vendored plugin tree.** *(M · [review])*

1,130 of 1,989 tracked files sit under `tasks/`, with copies of one plugin tree across
`humble-vs-super-v1`, `-v2`, `inject-content-v1` and two scenario asset dirs. ADR-0006 requires a real
tree for mount fidelity; it does not require five. Store snapshots once, content-addressed, with
per-bank manifests referencing them. **This collides with FATH-B15's constraint** — a mounted
directory's path is part of the arm's identity, so any relocation must preserve `tree_sha` semantics
and must not change the `config_hash` inputs of committed ledgers. Settle that first; if it cannot be
preserved, the dedup does not happen.

**FATH-B25 — A side study occupies three top-level directories and has produced no verdict.** *(M ·
[review])*

`scripts-rg2x2/`, `ledger-rg2x2/` and `streams-rg2x2/` hold 96 committed `.ndjson` streams (3.9 MB) and
two ad-hoc analysis scripts, and both the README and STATUS record no findings report. Either promote
the activation, gate-compliance and footprint tables into `fathom report` as proper views — they are
ledger-plus-stream derivations like every other view — or move the study out of the repo until it
produces a report. Decide deliberately whether raw streams belong in git: they are not regenerable by
re-render, only by re-spend, which argues for keeping them, but then they need a stated retention rule.
Closing the report is FATH-B06's work.

**FATH-B26 — A second runner adapter would make the vendor-neutrality claim true.** *(L · [review] +
[research])*

The `Runner` Protocol seam is cheap (104 lines) and already paid for, but after two months there is
exactly one adapter, so README and ADR-0001's claim that the framework must not be coupled to the
subscription CLI is aspiration presented as property. Downgrade the claim to "designed for, not yet
exercised" now (S), and treat a Codex or Gemini CLI runner as a real build item. The research supports
the strategic case: the closest open-source competitor now sits inside a model vendor, and provider
neutrality is named as a live reason to stay in-house. **Ordering note:** the review calls a second
adapter "the single highest-value build item", which sits oddly beside its own conclusion that the
highest-leverage change is converting prose rules into gates. It is placed here because the feedback
corpus contains zero occurrences of a blocked non-Claude eval — ordered by evidence, not by strategic
claim. Promote it the moment a real question needs a non-Claude arm.

**FATH-B27 — Economy is reported per trial, not per successful outcome.** *(S · [research])*

The landscape brief names cost-per-outcome with a defensible success denominator as something the
platforms structurally cannot compute and a local harness can. A cheaper arm with a lower pass rate is
more expensive per successful outcome, and the scorecard currently makes the reader do that division.
Add a cost-per-passing-trial column to the Economy table once FATH-B05 has made the underlying means
trustworthy.

**FATH-B28 — No deliberate way to render a chosen historical `dataset_version`.** *(S · [triage] T1c)*

The report scopes to the current (last-appended) dv and warns about excluded older-dv trials, which is
right, but there is no way to ask for the older view. Open since the first triage pass, still
uncorroborated.

**FATH-B29 — Two small CLI ergonomics fixes.** *(S · [triage] T13e + [review] + STATUS)*

`--no-engine-boundary` reads as disabling a safety control when it only skips a check group — rename to
`--skip-engine-check` (moot if FATH-B36 retires the engine group). And consider `--limit-per-arm N`
alongside the documented scenario-major behaviour of `--limit`, so a pilot cannot spend its whole
budget on the anchor arm; the reports converge on documenting first (FATH-B10), changing second.

**FATH-B30 — Record the buy-vs-build tripwire before it is needed.** *(S · [research])*

The landscape brief poses two questions this repo cannot answer ad hoc under pressure: at what
concurrent-experiment count does the absence of a comparison UI cost more than it saves, and could a
research-grade external harness that already drives coding agents as evaluated subjects do this? Write
the tripwire into STATUS — a named experiment count, and the named condition (a score moves and nobody
can say whether it was scorer drift or subject drift) that triggers a re-evaluation. This is
bookkeeping, not a decision; FATH-B45 records the decision as it stands today.

**FATH-B31 — Held at watch: rows with one occurrence and a concrete shape.** *(— · [triage])*

Not promoted, not dropped; each needs a second corroborating report or a first occurrence of real cost.
A gated-strategy arm meeting a bank whose tasks declare no `[gate]` degrades silently to a single spawn
(T9c). Classifying infrastructure halts as auth-expired vs usage-limit vs stall (T11c). Enforcing
`trial_timeout_s` out-of-band on a wall-clock timer (T11d) — this one turned an outage into the token
expiry cascade behind FATH-B04, so it is the likeliest to promote, and the cross-review adds that three
sibling repos are now paying for the same liveness class (a hung child no in-process deadline reaches),
which is corroboration from outside this corpus. Scripted multi-prompt session support: per-trial
config-dir lifecycle, a continue-session spawn mode, a `prompts = [...]` strategy (T15b) — **promoted by
the cross-review and carried as FATH-B47**: the collection routed its cadence and salience-decay arms
here explicitly because this adapter gives every trial exactly one user prompt, which is the second
blocked experiment this row was waiting for. Gate telemetry as ledger columns instead of a free-text
`detail` (T15c). Threading `max_fix_attempts` through so repair depth is sweepable (T15d).
Retain-result-view-on-fail if FATH-B14 proves insufficient (T5b). And from the first pass: a `@version`
re-vendor mismatch warn, design-effect-inflated Wilson as a mechanical guard if the K caveat proves
insufficient, and a docs reference-checker.

**FATH-B49 — Two `config_hash`es sharing an arm name are pooled in the economy views, so a tool-content
re-run reads as a truncated arm.** *(S · [wave-2 run])*

- **Cause / evidence:** `report.py` builds a `config_hash → scenario-name` map and then keys every
  view by the **name**. Pass Rates and Per-Criterion key on `(scenario, task, repeat)` with
  last-write-wins, so they correctly show the newer trials — but Economy, Efficiency and Arm Health
  sum the run rows of *every* hash carrying that name. The 2026-08-11 wave-2 re-run of
  `skill-pyeng-v1` against the merged skill body forked `pyeng-skill`'s hash without renaming the
  arm, and the scorecard reported `Sessions/Trial 2.00`, turns `94/102/111` (the two versions' turns
  summed per cell), and `Arm Health: 3/3 trials at/over max_turns` with the footnote that the arm's
  pass rate is "a **lower bound**, not a score". The real turns were `43/43/59` against a cap of 80.
  The verdict was recovered by aggregating the ledger by `config_hash` by hand — the same hand-join
  FATH-B13 records, now with a wrong *rendered* number attached rather than only a missing one.
- **Why it bites now:** re-running an existing arm against updated tool content is the standard
  shape of a re-validation, and it is what every cross-project gate re-check will do. The failure is
  silent and points the wrong way (it makes a healthy arm look truncated).
- **Change:** key the economy views by `(scenario, config_hash)` and render the hash prefix when a
  name carries more than one, or refuse-and-warn when a scoped `dataset_version` holds two hashes
  under one arm name. Pairs with FATH-B28 (no way to render a chosen historical view) and
  FATH-B11 (treatment identity vs the resume key).
- **Wave-3 recurrence, and the sharper statement of the rule** *(2026-08-12)*. The general form is
  narrower than "two hashes": **an arm re-run with changed injected content — new `config_hash`,
  same `name` — has its economy averaged with the old configuration's trials.** That is not an
  exotic case; it is what a re-validation *is*, so the defect fires on precisely the runs whose
  numbers get published. The fix statement follows from it: **aggregation keys on `config_hash`; the
  name is a label rendered beside the key, never the key itself.** The cost is already being paid in
  the corpus as a manual tax — the 2026-08-11 Opus 5 recalibration had to open with an explicit
  instrument check ("aggregating the ledger independently by `config_hash` returns five hashes for
  five names, one each — nothing pooled, so the scorecard's per-arm economy is read as-is") before
  its economy table could be trusted. A hand-check written into every report is the shape of an
  unbuilt invariant, and it fails silently the first time an author forgets it.

**FATH-B50 — A scenario whose treatment fails to load is warned about and then dropped, so the matrix
runs without it.** *(S · [wave-2 run])*

- **Cause / evidence:** authoring the `research-fusion-v1` arms in wave 2, the armed arm's
  `[plugins] mount` pointed at a tree that was not yet vendored. `fathom run --dry-run` printed
  `warning: skipping scenario fusion.toml: [Errno 2] ...plugin.json` and then planned the matrix
  **anyway** — `scenarios=1`, three trials, ceiling $6.00. Had that been a paid run it would have
  bought a full control arm, appended a ledger, and rendered a scorecard with no treatment in it at
  all. The `verify-arming` pre-flight cannot catch it, because a scenario that failed to load never
  reaches the list of arms to verify.
- **Why this is FATH-B01's class, not a papercut:** the whole argument of FATH-B01 is that an arm
  which is not armed can still produce a confident number. An arm that is *absent* produces a
  confident number too, and the only thing standing between the operator and that number is one
  warning line in a scroll of run output — the same "a check satisfied by absence" shape FATH-B12
  names in the smoke gate.
- **Change:** refuse the run when a scenario file in `--scenarios-dir` fails to load, with a
  dedicated exit code beside `EXIT_UNARMED` / `EXIT_BANK_INVALID`, and `--force` (or an explicit
  `--skip-broken-scenarios`) to proceed deliberately. Print the resolved arm count in the plan line
  beside the file count so a dropped arm is visible in the one line an operator always reads.

**FATH-B48 — This repo's skill and the collection's `evaluate-skill` claim the same job.** *(S ·
[cross-review])*

`fathom-eval`'s description triggers on "A/B this skill"; `evaluate-skill` in the collection triggers on
measuring whether a skill "beats the no-skill baseline (with/without)". That is one sentence written
twice, and neither description declines to the other, so both compete for the same dispatch and the
choice falls to whichever wording the operator happens to use. The boundary that actually exists is
clean: fathom owns the paid, scenario-blind matrix over a task bank — verifier-scored outcomes, economy
joined after scoring, an append-only ledger — while `evaluate-skill` owns trigger recall and specificity
(does the description fire on the right prompts and stay quiet on near-misses) plus the correct-usage
rubric. The with/without arm is the genuine overlap and should be assigned once, to the side already
spending on real tasks. Write the negative trigger into both descriptions naming the other, and state in
one line who owns the with/without comparison. Rides FATH-B21, which is already editing this repo's
skill surface.

---

## Retire / fold candidates

Each names its replacement. Nothing here is deleted for tidiness; each is either duplicated elsewhere,
displaced by a native primitive, or unexercised long enough that the evidence has spoken.

**FATH-B32 — Retire the MCP server and its three tools.** *(S · [review] + [research])*
`plan`, `report` and `smoke` each shell out to the CLI and return stdout inside a dict; the agent
already has Bash, and `smoke` is the one MCP tool that spends money, which is the worst fit for a
synchronous auto-invocable call — the same reasoning the repo already applied when it kept `run` off
MCP. **Replacement:** Bash plus the slash commands, with `fathom report` printing the rendered scorecard
path on its last line to carry over the one genuine addition. `_resolve.py`'s real logic — refusing a
plugin cache-clone or plugin root as `FATHOM_HOME`, which keeps the committed longitudinal ledger out
of a throwaway tree — moves into the stdlib core as `python -m fathom home`, with
`tests/test_packaging.py` repointed at it. Deleting the server also removes the plugin's only
third-party runtime dependency and its per-session subprocess, bringing packaging in line with the
stdlib-core invariant. `README-plugin.md`'s surface table needs one edit.

**FATH-B33 — Fold `/fathom:plan` into `/fathom:run`; cut `/fathom:report`'s duplicated body.** *(S ·
[review])*
`/fathom:plan` is `fathom run <bank> --dry-run` — the command file even appends the flag itself — and
its guardrail prose is verbatim duplication. Two-thirds of `/fathom:report` is a copy of the skill's
scorecard-reading section. **Replacement:** make `/fathom:run` dry-run first and require explicit
confirmation before spending, so one verb tells one story; cut the report command's reading guidance to
a one-line pointer and let the skill own interpretation.

**FATH-B34 — Retire the pairwise judge.** *(S · [review] + [research])*
299 lines shipped dark since 2026-06-10, referenced only by its own test — never by `cli.py`,
`report.py` or any strategy. Its cost is not zero: a `GradingRecord` in the ledger schema, a
permanently empty "Pairwise vs Bare Anchor" section in every scorecard, and a "this is always empty"
caveat repeated in four places that must be edited together. All 14 completed analyses reached their
verdicts without it, and STATUS itself notes that fuzzy-rubric gold-set kappa is weak evidence while
verifier-expressible criteria are preferable — a position the landscape brief reinforces (judge
agreement is not truth without human adjudication). **Replacement:** verifier-expressible criteria,
which is what every verdict already rests on. Delete the module, its test, `GradingRecord`, the
scorecard section and the four caveats, and drop "light up the judge" from STATUS's next-steps — this
backlog reverses that ordering. The code is recoverable from git; a future quality axis should be
re-derived against human adjudication rather than un-parked.

**FATH-B35 — Fold `gated-review` into `gated-session`.** *(S · [review])*
It is `gated-session` plus one structured review pass, already implemented as a `with_review` flag on
the same executor. It has two scenario files, both in one bank, and STATUS records the strong-tier
result as +0 for every in-session feature — yet it costs a distinct name enumerated in four documents
plus a rejection path in the parser. **Replacement:** a `review = true` scenario key on
`gated-session`; existing arms migrate by adding the key, and the old name stays accepted for one
release so committed `config_hash`es remain interpretable.

**FATH-B36 — Retire the `series` strategy, its contract spec and smoke group 4 — conditional on
FATH-B17.** *(M · [review] + [research])*
Two months, one negative result, unexercised since, one outage caused. **Replacement:** native
subagents, agent teams and worktree isolation for mechanical fan-out; the residual claim
(dependency-ordered execution under per-phase budgets with gates that can reject "done") is exactly
what FATH-B17 measures. Do not retire before that measurement runs — it is cheap and the instrument
exists. If it retires, the smoke check count drops to 7 and `--no-engine-boundary` disappears with it.

**FATH-B37 — Fold the six generic `docs/method/` files to upstream pointers.** *(S · [review])*
`definition-of-ready`, `definition-of-done`, `review-checklist`, `pre-mortem-prompt`,
`reflection-triage` and `series-toml-skeleton` are a per-project copy of a portable method kit that the
method plugin owns upstream; each copy drifts independently, and one of them is already listed as a
hand-maintained mirror. The generic content is not fathom knowledge. **Replacement:** pointers to the
installed method plugin's originals from `docs/method/README.md`. Keep `method-bindings.md` — the
binding to this repo's actual gate commands is the local content and cannot live upstream. Coordinate
with FATH-B10, which currently points at `review-checklist.md`.

**Cross-review — two files in this directory are registered mirror sites; deregister them in the same
change.** The operator's model-mirror table registers `series-toml-skeleton.md` (one of the six, for its
pinned tier examples, which are written in family names rather than tier words) and, in the same
directory, `recalibration-playbook.md` — whose registration exists precisely to record that its Step 0
defers to the single mirror owner. Folding either to a pointer without editing that table in the same
change leaves the registry pointing at deleted paths, which is the exact failure CRAF-B13 proposes a
bindings file to prevent, and it silently drops the deferral that keeps the playbook from re-deriving
model policy. So: fold the other files freely, and for these two either keep them or fold them with the
registry rows updated in the same change. Half of this is worse than none of it.

**FATH-B38 — Archive `pr-series/` out of the repo.** *(S · [review])*
27 tracked PR briefs and two `series.toml` files for the series that built fathom, with no consumer;
the decisions they encode already live in the ADRs and the build spec, and the briefs are the
intermediate execution form. **Replacement:** the ADRs and build spec for the decisions; if a
conformance fixture for the engine contract is wanted, move one `series.toml` under `tests/fixtures/`
and keep only that. One series could go to the method plugin as a worked example, where a method
exemplar has an audience.

**FATH-B39 — Delete the two empty bank remnants.** *(S · [review])*
Two directories under `tasks/` hold no bank. **Replacement:** nothing — they are residue. The
serena-nav pair is a separate case with a live conclusion attached and is handled by FATH-B20, not
here.

---

## Declined

Recorded so they are not relitigated. Each names why, and what would reopen it.

**FATH-B40 — `--emit-record-fragment`.** Designed and then deliberately dropped by its own author to
keep that wave single-repo; the downstream bridge reads the ledger directly and works without it.
FATH-B07 serves the same consumer need at lower cost. Reopen only if a consumer appears that cannot
read the ledger. *(from `2026-07-24-experiment-rigor-bridge-design#3`)*

**FATH-B41 — `arm_tier` substring resolution misclassifying a mixed-family bank.** Accepted, no action.
It is harmless today because such arms live only in banks without `scores.toml`, so the calibration
build never runs on them, and the documented per-bank `[arms]` override is the escape hatch. Reopen if
such a bank ships. *(from `2026-07-14-model-selection-rollout-recovery#3`)*

**FATH-B42 — Harness-user monitoring and analysis discipline.** Reading errored ledger rows as real
negatives, and probing arming only on suspicion, are operator practices. The tool's share of both is
already promoted — FATH-B03 makes un-run trials unscoreable and FATH-B01 makes arming a gate — and the
residual is not a fathom surface. *(from `2026-07-25-dispatch-phase2-subagent-arms` §Friction and
`2026-07-25-serena-nav-arming-defect` §Vacuous gates)*

**FATH-B43 — A wave-orchestration stream that erased itself and produced no worktree, branch or
partial.** Routed out to the multi-stream orchestration harness that ran the wave; already filed in
that tool's own recovery report. fathom keeps nothing — it is recorded only because one calibration leg
was among the casualties, and the bank was recovered by hand. *(from
`2026-07-14-model-selection-rollout-recovery` §Misses)*

**FATH-B44 — Two one-concern PRs that both append a test class after the same anchor and conflict on
the second merge.** Routed out to the series and PR-splitting guidance in the method tooling — prefer
stacking, or end-of-file test placement, when several one-concern PRs touch a shared test module. A
wave-decomposition lesson, not a fathom surface. *(from
`2026-07-14-model-selection-rollout-recovery#2`)*

**FATH-B45 — Replacing the harness with a rented eval platform.** Declined as of this pass. The
platforms A/B prompts and models over a fixed scaffold; fathom's unit of variation is the scaffold
itself — skill armed vs bare, strategy, effort tier — which is the axis they hold constant. Blind
scoring is a construction here, not a toggle, and is awkward to retrofit onto a UI built around
labelled side-by-side comparison. The banks and the append-only ledger are the part that is not
copyable. What is genuinely better elsewhere — the comparison UI, statistical rigour over factorial
designs, and commodity operational surface — is real, so FATH-B30 records the tripwire that would
reopen this rather than leaving it to mood. *(from the landscape brief)*

**FATH-B46 — Replacing the pooled Wilson interval with cluster-t or bootstrap.** Evaluated by a blind
review panel and declined: both collapse at K=1 banks and on all-0 or all-100 tasks, which is worse
than Wilson. The chosen resolution — keep the pooled point and interval, state the clustering caveat
plainly, and surface K beside n — stands. The escalation (a design-effect-inflated Wilson as a
mechanical guard) is held at watch in FATH-B31, not declined. *(from the 2026-07-05 audit)*
