# Does injected dispatch content change bug-fix outcomes? — inject-content-v1 findings

- **Date:** run 2026-07-23 (ledger committed the same day, `a8d26e3`); report 2026-08-11.
  Bank: `inject-content-v1` (5 bug-fix tasks vendored from the `humble-vs-super-v3`/`-v4`
  banks × 2 instruction registers = 10 tasks). Written from the committed ledger and the
  regenerated scorecard; until now the conclusions survived only in the commit message,
  and `docs/STATUS.md` carried the bank as **Unreported**.
- **Question (operator):** with the same toolkit mounted in every arm, does *injecting*
  dispatch content into the system prompt change bug-fix outcomes — and does the generic
  8-step dispatch protocol (what an always-on injected surface delivers) beat injecting
  nothing at all?

## What was run

3 arms × 10 tasks × 1 repeat = **30 trials**, single-session, `claude-sonnet-5`, effort
high, headless default-deny, 1200-s trial cap and `max_turns = 120`.
Dataset_version `1`; **30/30 completed**, every run row `exit_code = 0`, zero infra
errors, zero holdout, no archived/invalid rows.

The arms are a clean single-factor contrast — same three plugins vendored into the bank
and mounted identically (`humblepowers` 0.7.4, `engineering-discipline` 0.3.0,
`session-workflow` 0.19.0), same tool allow-list, same model, effort and strategy. The
**only** difference between the three scenario files is `[context] inject`:

| Arm | Injected content |
|---|---|
| `bare` | none — toolkit mounted and loadable, nothing appended to the system prompt |
| `nudge` | 2 lines naming the two candidate skills for a bug fix (`systematic-debugging`, `test-driven-development`), with "set aside plainly if not" |
| `protocol` | the 8-step generic dispatch protocol verbatim from the plugin's injected block |

The bank smuggles a second factor into the task-id suffixes: five base bugs
(`fix-dedup-records`, `fix-interval-merge`, `fix-money-split`, `fix-nonlocal-parse`,
`fix-nonlocal-urlkey`) each authored in two instruction registers — `-embedded` (the
intent buried in a longer working message) and `-paraphrase` (the situation described
without bug/fix vocabulary). Both registers are the ones a lexical router cannot reach.
Every task also carries the two universal criteria `no_regression` and
`regression_test_present` from the shared bug-fix verifier.

## Result

| Arm | Pass | Pass rate | Wilson 95% CI | K (distinct tasks) | Infra errors |
|---|---|---|---|---|---|
| `bare` | 9/10 | 90.0% | [59.6%, 98.2%] | 10 | 0 |
| `nudge` | 10/10 | 100.0% | [72.2%, 100.0%] | 10 | 0 |
| `protocol` | 9/10 | 90.0% | [59.6%, 98.2%] | 10 | 0 |

`bare` and `protocol` are the *same* point estimate with the *same* interval. All three
intervals overlap over most of their length. Fisher's exact on `protocol` vs `bare` is
p = 1.0; on `nudge` vs `bare`, p = 1.0.

**The per-criterion view is the real read, and it says the two misses are unrelated
failure modes on different tasks, not a graded effect.** Twelve of the fourteen criteria
are at 100% in every arm. Only three cells are not:

| Criterion | `bare` | `nudge` | `protocol` | Where |
|---|---|---|---|---|
| `regression_test_present` | 90.0% (9/10) | 100.0% (10/10) | 100.0% (10/10) | `fix-nonlocal-urlkey-paraphrase` |
| `codes_quoted_tagged` | 100.0% (2/2) | 100.0% (2/2) | 50.0% (1/2) | `fix-nonlocal-parse-embedded` |
| `messages_quoted` | 100.0% (2/2) | 100.0% (2/2) | 50.0% (1/2) | `fix-nonlocal-parse-embedded` |

- **`bare`'s one failure is test-hygiene, not correctness.** On
  `fix-nonlocal-urlkey-paraphrase` the fix itself was correct (`page_counts_merge`,
  `top_page_merge` and `no_regression` all passed); no candidate-added test failed when
  the buggy original was swapped back in, so `regression_test_present` scored false.
- **`protocol`'s one failure is correctness, not hygiene.** On
  `fix-nonlocal-parse-embedded` both behavioral criteria failed together while
  `no_regression` and `regression_test_present` passed — the shape of a patch that
  satisfies the shipped suite and the candidate's own new test without repairing the
  underlying parse. The commit message calls this a "root-cause band-aid"; the ledger
  supports the *description* of that trial, not a claim that the protocol arm is prone
  to it.
- **`nudge` is the only arm with a clean sheet**, in both registers, at no extra cost
  beyond noise. That is one trial's worth of separation from the other two.

### Arm × register (hand-derived from the ledger; the report cannot render it)

The scorecard **pools** the two registers, because the register lives in the task-id
suffix rather than in a bank-level factor the report understands. Joining the `trial`
rows on `scenario` × `task_id` (`kind == "trial"`, `status == "completed"`, all 30 rows)
splits it out:

| Arm | `-embedded` | `-paraphrase` | Pooled |
|---|---|---|---|
| `bare` | 5/5 (100%) | 4/5 (80%) | 9/10 |
| `nudge` | 5/5 (100%) | 5/5 (100%) | 10/10 |
| `protocol` | 4/5 (80%) | 5/5 (100%) | 9/10 |

Each cell is n=5 — Wilson [56.6%, 100.0%] for 5/5 and [37.6%, 96.4%] for 4/5. The two
failures land in opposite registers, which is what a two-event scatter looks like.
**No register effect is visible and none could be at this cell size**; the split is
reported because the factor exists in the bank and a pooled table hides it, not because
it discriminates. Rendering it natively is a known reporting gap: `fathom report` has no
notion of a task-id-encoded factor.

Base task × arm is equally flat — every base bug is 2/2 in every arm except
`fix-nonlocal-parse` (`protocol` 1/2) and `fix-nonlocal-urlkey` (`bare` 1/2).

### Economy

| Arm | Est. USD | Turns | Wall (sum) | Mean out-tokens | Quality/100k tok |
|---|---|---|---|---|---|
| `bare` | $3.62 | 117 | 433.7 s | 2,515 | 0.16 |
| `nudge` | $3.87 | 130 | 403.4 s | 2,464 | 0.18 |
| `protocol` | $3.55 | 109 | 411.8 s | 2,347 | 0.16 |

Whole matrix: **$11.05 estimated, 356 turns, 20.8 min of summed trial time** (the commit
records ~41 min of matrix wall-clock including verification). The spread across arms is
±8% on USD and ±10% on turns — within noise at n=10, and note the direction: `protocol`,
which injects the *most* content, was the **cheapest** arm here. Per the D2 note in
STATUS, USD is a token×price estimate under subscription auth; tokens and turns are the
primary economy currency.

### Register × economy

| Arm | `-embedded` | `-paraphrase` |
|---|---|---|
| `bare` | $2.03 / 68 turns | $1.59 / 49 turns |
| `nudge` | $2.18 / 74 turns | $1.69 / 56 turns |
| `protocol` | $1.90 / 61 turns | $1.65 / 48 turns |

The register moves cost more than the arm does (embedded instructions run ~20-30% dearer
in every arm, consistently), which is a property of the longer instructions, not of
dispatch.

## Verdict

**Injecting the generic 8-step dispatch protocol did not beat injecting nothing on this
bank: 9/10 versus 9/10, identical Wilson intervals [59.6%, 98.2%], Fisher p = 1.0.**
The observed difference is zero.

What that does and does not establish, precisely:

1. **It does not establish a benefit.** There is no measurable pass-rate advantage to the
   always-on injected protocol over the same toolkit with an empty `[context]`. Nor is
   there one in economy: the protocol arm was, if anything, marginally cheaper.
2. **It equally does not establish harm, or absence of effect.** A zero difference at
   n=10 per arm is not a demonstration that the surface does nothing. With 9/10 versus
   9/10 the 95% interval on the *difference* spans roughly ±30 percentage points; effects
   well inside that band are entirely compatible with this result. **The honest statement
   is "no measurable difference at this power", not "no effect".**
3. **A decision to retire an always-on injected dispatch surface can cite this analysis
   only for the negative claim** — that the surface has not been shown to buy anything on
   measured bug-fix outcomes, so its cost (context, anchoring, maintenance) is currently
   unjustified by evidence. A retirement argued that way is defensible. An argument that
   this run *measured the surface to be useless*, or that it proved the injection
   harmless to remove, overreads the data.
4. **The one arm that swept was itself an injected surface.** `nudge` — two lines naming
   concrete candidate skills — went 10/10 in both registers at parity cost. Its edge over
   `bare` is a single trial (Fisher p = 1.0), so it is not a separation either. But
   whatever this bank supports about injection points at *content*, not at injection
   per se: the generic protocol tied `bare`, and the concrete naming is the only arm that
   did not drop a trial. Treat that as a hypothesis worth powering, not a result.
5. **This bank measures outcomes only.** The verifiers score the finished workspace. They
   say nothing about whether any skill was actually loaded in any arm — the recall/trigger
   axis is not instrumented here, so "did the injection change dispatch behavior?" is
   untouched even where "did it change the outcome?" is answered.

## Limitations

- **Power is the binding constraint. n=10 per arm across K=10 distinct tasks, 1 repeat
  each.** No arm ordering in this bank is distinguishable from noise: the three arms
  differ by at most one trial, all pairwise Fisher tests return p = 1.0, and the Wilson
  intervals [59.6%, 98.2%] / [72.2%, 100.0%] / [59.6%, 98.2%] overlap almost entirely.
  Per the scorecard's standing caveat, those intervals are a *heuristic width* anyway —
  they pool ten heterogeneous tasks as independent draws, so they under-state the true
  uncertainty rather than over-state it.
- **The bank ceilings.** 28 of 30 trials passed everything. When the control arm already
  sits at 90%, the largest lift any treatment can demonstrate is +10 pp — one trial. This
  is the same ceiling that STATUS records for the `humble-vs-super-v3`/`-v4` banks
  (0/180 correctness failures at n=45): on self-contained, deterministically-verifiable
  bug fixes, a capable model gets there regardless of dispatch content. A bank that could
  answer this question needs a control arm that fails often enough to leave room.
- **The arm × register split is n=5 per cell.** It is included for completeness and to
  document a factor the scorecard hides; it carries no inferential weight.
- **One model, one effort, one strategy.** `claude-sonnet-5` at effort high in a single
  session. Nothing here transfers to the weak tier, to long multi-session work, or to
  the multi-prompt cadence the injected surface actually runs under in practice.
- **Cadence was out of scope by construction.** The commit records this as phase 1 of a
  cadence-versus-content question, content only: the cadence arms need scripted
  multi-prompt sessions the claude-cli adapter does not support. An always-on surface
  injects on *every* prompt; this bank tests a single prompt-1 injection. Whatever
  per-prompt repetition does — for good or ill — is unmeasured.
- **Register pairs are not independent.** Each register pair shares a base bug, fixtures
  and verifier, so the ten tasks are five correlated pairs. K=10 overstates the effective
  number of distinct problems.
- **Estimated USD, not billed USD** (STATUS D2): subscription auth reports
  `total_cost_usd = 0`, so the figures above are the adapter's token×price estimate.

## Related

- The outcome-side follow-up ran the same day across three per-discipline banks:
  `2026-07-23-e1-debug-findings.md`, `2026-07-23-e1-data-findings.md`,
  `2026-07-23-e1-verif-findings.md`.
- Ledger: `ledger/inject-content-v1.jsonl` (30 trial rows + 30 run rows, append-only).
  Regenerate the scorecard with `uv run fathom report inject-content-v1`;
  `report/` is gitignored.
