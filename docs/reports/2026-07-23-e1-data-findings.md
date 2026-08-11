# Does injecting dispatch candidates change data-correctness behavior? — e1-data findings

- **Date:** run 2026-07-23 (ledger committed the same day, `11e6447`, merged `86e7060`);
  report 2026-08-11. Bank: `e1-data` (2 aggregation tasks, each with an easy case and a
  subtle case a naive fix misses). One of three per-discipline banks in the same
  experiment — companions `2026-07-23-e1-debug-findings.md` and
  `2026-07-23-e1-verif-findings.md`. Written from the committed ledger and the
  regenerated scorecard; `docs/STATUS.md` carried the bank as **Unreported**.
- **Question (operator):** does injecting concrete dispatch candidates into the system
  prompt change the *outcome* of a data-correctness task — specifically, whether the
  agent verifies the actual output against the real input rather than inferring
  correctness from the code — and does that depend on model tier?

## What was run

8 arms (4 content × 2 tiers) × 2 tasks × 1 repeat = **16 trials**, single-session,
effort medium, headless default-deny, 600-s trial cap, `max_turns = 40`.
Dataset_version `1`; **16/16 completed**, every run row `exit_code = 0`, zero infra
errors, zero holdout.

Tiers: `claude-haiku-4-5` (weak) and `claude-sonnet-5` (mid). Every arm mounts the same
three plugins (`humblepowers`, `engineering-discipline`, `session-workflow`) with the
same tool allow-list; the arms differ **only** in `[context] inject`:

| Content arm | Injected content |
|---|---|
| `bare` | none — toolkit mounted and loadable, nothing appended |
| `oracle` | names the one right discipline for this bank (data-correctness: verify the actual output against the input; watch for quiet row drops, duplication, boundary miscounts) — the upper bound of a perfect semantic router |
| `registry` | the full static list of ~19 installed skills with one-line "when each applies" |
| `classifier` | what an offline prompt-classifier would emit: two ranked candidates for this prompt |

**Tasks** — each instruction reports only a vague symptom ("the totals look off"), and
each verifier carries its own canonical input so the subtle rows are always present:

- `expense-rollup` — a category rollup drops blank-category rows. The easy case is the
  fully-categorized buckets; the subtle case is whether the breakdown and grand total
  account for every amount. A fix that only patches the grand total still fails.
- `order-merge` — a customer lookup carries a duplicate row, so a join fans out and
  inflates one region's revenue. The untouched region is the easy case; the inflated
  region is the subtle case. Deduplicating the already-unique orders instead of the
  lookup leaves the fan-out.

The verifier emits `output_correct_on_easy_case` and `output_correct_on_subtle_case`
(the gate and the discriminating proxy).

## Result

| Arm | Pass | Pass rate | Wilson 95% CI | K | Infra errors |
|---|---|---|---|---|---|
| `bare-haiku` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |
| `oracle-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `registry-haiku` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |
| `classifier-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `bare-sonnet` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `oracle-sonnet` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |
| `registry-sonnet` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |
| `classifier-sonnet` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |

**The per-criterion view collapses this to a single question asked once per arm.**

| Criterion | Result |
|---|---|
| `output_correct_on_easy_case` | **100% in all eight arms (16/16 trials)** |
| `output_correct_on_subtle_case` | the only discriminating criterion — 13/16 |

- **The easy case is saturated.** Every trial in every arm produced correct
  fully-categorized buckets and a correct untouched region. Everything this bank measures
  is the subtle case.
- **The subtle case is carried by exactly one task.** `expense-rollup` passed in all
  eight arms (16/16, both criteria); every failure in the bank is `order-merge`'s
  `output_correct_on_subtle_case` — the join fan-out. Three trials failed it:
  `bare-sonnet`, `oracle-haiku`, `classifier-haiku`.
- **So the effective design is 8 arms × 1 discriminating trial each.** Five of eight came
  up heads and the three tails do not line up with any content ordering: the
  perfect-router `oracle` arm failed at the weak tier and passed at the mid tier, while
  `bare` did the reverse. `bare-haiku` — the arm with nothing injected on the weakest
  model — is one of the five that scored 2/2.
- The blank-category rollup, designed as the harder trap, turned out not to be a trap at
  all at either tier; the duplicate-lookup fan-out was the one that bit.

### Economy

| Arm | Est. USD | Turns | Mean out-tok | Mean wall (s) |
|---|---|---|---|---|
| `bare-haiku` | $0.155 | 23 | 1,870 | 31.4 |
| `oracle-haiku` | $0.176 | 23 | 1,843 | 31.6 |
| `registry-haiku` | $0.215 | 32 | 2,622 | 44.9 |
| `classifier-haiku` | $0.142 | 20 | 1,735 | 29.5 |
| `bare-sonnet` | $0.535 | 17 | 1,335 | 26.1 |
| `oracle-sonnet` | $0.596 | 21 | 2,098 | 31.2 |
| `registry-sonnet` | $0.980 | 12 | 1,524 | 24.5 |
| `classifier-sonnet` | $0.748 | 22 | 2,439 | 40.0 |

Bank total **$3.54 estimated, 170 turns, 8.6 min** of summed trial time — $0.69 across
the eight haiku trials and $2.86 across the eight sonnet trials, a ~4× tier cost ratio
for no measurable quality difference in this bank. One `registry-sonnet` trial
(`order-merge`) completed in a single turn, which is what pulls that arm's mean turn
count down while its USD stays high. USD is the adapter's token×price estimate under
subscription auth (STATUS D2).

### The cross-bank pooling this run's decision actually rested on

The commit message reports a pooled figure, not this bank's. Pooling the identical arm
structure across all three `e1-*` banks gives n=6 per (content × tier) cell:

| Tier | `bare` | `oracle` | `registry` | `classifier` |
|---|---|---|---|---|
| haiku | 4/6 | 4/6 | 4/6 | 3/6 |
| sonnet | 2/6 | 3/6 | 4/6 | 6/6 |

The pre-registered kill gate keyed on the weak-tier cell: `oracle` tied `bare` at 4/6,
Fisher p = 1.0. The unexpected mid-tier gradient runs the other way — `bare` 2/6 to
`classifier` 6/6, Fisher p = 0.061, which does not clear 0.05 and rests on 24 trials
spread over three different banks and six different tasks.

## Verdict

**On this bank, nothing separates the arms.** The easy-case gate is saturated at 16/16,
the discriminating proxy resolves to one trial per arm on one task, and the three
failures are scattered across content arms and tiers with no ordering — including one on
the perfect-router arm at the weak tier and one on the control arm at the mid tier.

What this bank does establish, narrowly:

1. **The instrument half-works.** The duplicate-lookup fan-out in `order-merge` is a real
   discriminating trap: 3 of 8 arms shipped an inflated region while passing everything
   else. The blank-category trap in `expense-rollup` is not — 16/16 — and should be
   re-authored or replaced before this bank is run again.
2. **A vague symptom report is enough to elicit the behavior.** Both instructions
   describe only "the numbers look off" and never name the mechanism; agents still
   located and mostly repaired the aggregation defect. The task shape is sound.
3. **It does not establish anything about injected dispatch content.** Not a benefit, not
   harm, not equivalence. One draw per arm cannot rank eight arms.

## Limitations

- **Power is the binding constraint, and it is severe. n=2 per arm — 2 tasks × 1 repeat
  — over 8 arms, 16 trials in total.** With n=2 the Wilson interval for a perfect arm is
  [34.2%, 100.0%] and for a half-passing arm [9.5%, 90.5%]; every arm's interval contains
  every other arm's point estimate. **No arm ordering in this bank is distinguishable
  from noise**, and none should be quoted as a finding.
- **Effectively n=1.** Because `output_correct_on_easy_case` and `expense-rollup` are
  both saturated, each arm's score is decided by a single trial (`order-merge`). Eight
  one-trial arms.
- **The pooled cross-bank reading is thin too.** n=6 per cell, and it pools three banks
  with different disciplines, tasks and verifiers as though they were repeats of one
  experiment. The weak-tier tie (4/6 vs 4/6) is a legitimate basis for a pre-registered
  *stop* decision, but it is not a demonstration that injection has no effect. The
  mid-tier gradient (2/6 to 6/6, p = 0.061) is at best a hypothesis; the commit message
  correctly calls it underpowered.
- **The mounted plugins live outside this repo.** These scenarios mount
  `C:/Users/grima/Documents/craft-collection/plugins/...` by absolute path rather than
  vendoring them into the bank. Their content tree_sha enters `config_hash`, so the run
  is *pinned*, but it is not *reconstructible* from this repository alone.
- **One repeat, two tiers, one strategy, one effort.** Single-session, effort medium; the
  strong tier was not run.
- **Outcome-only.** The verifiers score the finished workspace. Whether any arm actually
  loaded a skill — the recall axis the injected content is meant to move — is not
  instrumented in this bank.
- **Estimated USD, not billed USD** (STATUS D2).

## Related

- Companion banks from the same run: `2026-07-23-e1-debug-findings.md`,
  `2026-07-23-e1-verif-findings.md`. Content A/B on a larger bug-fix bank:
  `2026-07-23-inject-content-v1-findings.md`.
- Ledger: `ledger/e1-data.jsonl` (16 trial rows + 16 run rows, append-only). Regenerate
  the scorecard with `uv run fathom report e1-data`; `report/` is gitignored.
- A later re-run of the same three banks under a different arm structure sits unreported
  in `ledger-rg2x2/` + `streams-rg2x2/` and is **not** covered here.
