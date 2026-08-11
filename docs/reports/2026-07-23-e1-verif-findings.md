# Does injecting dispatch candidates change verification behavior? — e1-verif findings

- **Date:** run 2026-07-23 (ledger committed the same day, `11e6447`, merged `86e7060`);
  report 2026-08-11. Bank: `e1-verif` (2 single-function fixes with a swap-the-bug-back
  proxy for "left a guard before declaring done"). One of three per-discipline banks in
  the same experiment — companions `2026-07-23-e1-debug-findings.md` and
  `2026-07-23-e1-data-findings.md`. Written from the committed ledger and the regenerated
  scorecard; `docs/STATUS.md` carried the bank as **Unreported**.
- **Question (operator):** does injecting concrete dispatch candidates into the system
  prompt change the *outcome* of a fix-and-verify task — specifically, whether the agent
  leaves behind a check that would fail if the fix regressed — and does that depend on
  model tier?

## What was run

8 arms (4 content × 2 tiers) × 2 tasks × 1 repeat = **16 trials**, single-session,
effort medium, headless default-deny, 600-s trial cap, `max_turns = 40`, verifier
timeout raised to 120 s (the proxy runs the candidate's suite twice).
Dataset_version `1`; **16/16 completed**, every run row `exit_code = 0`, zero infra
errors, zero holdout.

Tiers: `claude-haiku-4-5` (weak) and `claude-sonnet-5` (mid). Every arm mounts the same
three plugins (`humblepowers`, `engineering-discipline`, `session-workflow`) with the
same tool allow-list; the arms differ **only** in `[context] inject`:

| Content arm | Injected content |
|---|---|
| `bare` | none — toolkit mounted and loadable, nothing appended |
| `oracle` | names the one right discipline for this bank (prove a change works before declaring it done; leave a check that would fail on regression) — the upper bound of a perfect semantic router |
| `registry` | the full static list of ~19 installed skills with one-line "when each applies" |
| `classifier` | what an offline prompt-classifier would emit: two ranked candidates for this prompt |

**Tasks** — both are fully-specified single-function fixes with a documented contract, so
the correctness gate is meant to be easy and the proxy is meant to carry the signal:

- `even-split` — `split_amount` drops the remainder; the contract says distribute it to
  the earliest shares so they sum exactly and come out non-increasing.
- `tag-normalize` — `normalize_tags` lets case-insensitive repeats through; the contract
  says keep only the first occurrence, in order.

The verifier emits `spec_met` (the correctness gate, computed by importing the candidate
directly) and `regression_check_present` — the proxy: run the candidate's own checks
(must be green), then swap the stashed buggy original back in on a throwaway copy and
re-run (must go red). The shipped baseline checks pass on the buggy source by
construction, so a red can only come from a candidate-added check that pins the edge.

## Result

| Arm | Pass | Pass rate | Wilson 95% CI | K | Infra errors |
|---|---|---|---|---|---|
| `bare-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `oracle-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `registry-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `classifier-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `bare-sonnet` | 0/2 | 0.0% | [0.0%, 65.8%] | 2 | 0 |
| `oracle-sonnet` | 0/2 | 0.0% | [0.0%, 65.8%] | 2 | 0 |
| `registry-sonnet` | 0/2 | 0.0% | [0.0%, 65.8%] | 2 | 0 |
| `classifier-sonnet` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |

**The per-criterion view collapses this to one question, asked twice per arm.**

| Criterion | Result |
|---|---|
| `spec_met` | **100% in all eight arms (16/16 trials)** — every trial fixed the function correctly |
| `regression_check_present` | the only discriminating criterion — **6/16 (37.5%)** overall |

- **The correctness gate is saturated.** No trial in any arm failed `spec_met`. Every
  headline number above is the proxy, unchanged.
- **Unlike the two companion banks, both tasks discriminate here.** `even-split`'s proxy
  passed in 2 of 8 arms (`classifier-haiku`, `classifier-sonnet`); `tag-normalize`'s in 4
  of 8 (`bare-haiku`, `oracle-haiku`, `registry-haiku`, `classifier-sonnet`). So each arm
  contributes two informative trials rather than one — this is the only one of the three
  banks whose n=2 is genuinely n=2.
- **The strongest-looking pattern in the whole experiment sits here, and it is still
  n=2.** Every mid-tier arm except `classifier-sonnet` scored 0/2 on the proxy, at 3-8
  turns per trial; the weak-tier arms scored 1/2 each at 5-19 turns. Pooled by tier that
  is haiku 4/8 versus sonnet 2/8 on the proxy — the faster, more capable model fixed the
  bug and left nothing behind more often. That is a plausible mechanism (fewer turns,
  more confidence, less scaffolding) and it is **not** established by 16 trials.
- **`classifier-sonnet` is the single arm that swept**, and it is the same arm that
  carries the mid-tier gradient in the pooled cross-bank view. It is two trials.

### Economy

| Arm | Est. USD | Turns | Mean out-tok | Mean wall (s) |
|---|---|---|---|---|
| `bare-haiku` | $0.194 | 27 | 2,554 | 42.0 |
| `oracle-haiku` | $0.202 | 27 | 2,746 | 44.7 |
| `registry-haiku` | $0.141 | 18 | 1,721 | 25.2 |
| `classifier-haiku` | $0.240 | 36 | 3,646 | 58.5 |
| `bare-sonnet` | $0.411 | 9 | 528 | 12.9 |
| `oracle-sonnet` | $0.514 | 15 | 975 | 20.4 |
| `registry-sonnet` | $0.462 | 11 | 766 | 17.3 |
| `classifier-sonnet` | $0.569 | 17 | 1,384 | 31.6 |

Bank total **$2.73 estimated, 160 turns, 8.4 min** of summed trial time — $0.78 across
the eight haiku trials and $1.96 across the eight sonnet trials. The turn and
output-token columns track the proxy result closely: the arms that left a regression
check spent more turns doing it, at both tiers. That association is descriptive, not
causal, and it is the same 16 trials. USD is the adapter's token×price estimate under
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
spread over three different banks and six different tasks. Four of the six mid-tier
`bare` failures come from this bank.

## Verdict

**On this bank, nothing separates the arms.** The correctness gate is saturated at
16/16; the proxy splits 6/16 with seven of the eight arms scoring 0/2 or 1/2 and one
arm scoring 2/2. A single arm ahead by one trial over its tier-mates, on a bank where
every arm has two trials, is not a separation.

What this bank does establish, narrowly:

1. **The instrument is the best of the three.** Both tasks discriminate, the
   swap-the-bug-back proxy is behavioral rather than textual, and the base rate (37.5%)
   sits far enough from both ceilings to leave room for an effect to show. This is the
   bank shape to keep and power up.
2. **Leaving a regression check is not the default behavior at either tier.** Ten of
   sixteen trials fixed a documented contract correctly and left nothing that would catch
   the bug coming back. That is a robust observation about the base rate — it does not
   depend on separating arms — and it is the finding most worth carrying forward.
3. **It does not establish anything about injected dispatch content.** Not a benefit, not
   harm, not equivalence. Nor does it establish the tier pattern it hints at.

## Limitations

- **Power is the binding constraint, and it is severe. n=2 per arm — 2 tasks × 1 repeat
  — over 8 arms, 16 trials in total.** With n=2 the Wilson interval for a perfect arm is
  [34.2%, 100.0%], for a half-passing arm [9.5%, 90.5%], and for a zero arm
  [0.0%, 65.8%]; those intervals overlap across every pair of arms in the table. **No arm
  ordering in this bank is distinguishable from noise**, and none should be quoted as a
  finding — including the `classifier-sonnet` sweep and the haiku-beats-sonnet proxy
  pattern, both of which are the kind of shape two trials produce by chance routinely.
- **The pooled cross-bank reading is thin too.** n=6 per cell, and it pools three banks
  with different disciplines, tasks and verifiers as though they were repeats of one
  experiment. The weak-tier tie (4/6 vs 4/6) is a legitimate basis for a pre-registered
  *stop* decision, but it is not a demonstration that injection has no effect. The
  mid-tier gradient (2/6 to 6/6, p = 0.061) is at best a hypothesis; the commit message
  correctly calls it underpowered.
- **The proxy has a known false negative** (documented in both verifiers): a heavy
  refactor that relocates the logic out of the swapped module defeats the swap and scores
  false regardless of what the candidate left behind. The "keep the public API unchanged"
  instruction makes it rare but not impossible, and no trial-level evidence distinguishes
  a genuine miss from this artifact.
- **`spec_met` being saturated is by design and also a limitation** — this bank cannot
  say anything about correctness, only about the verification footprint.
- **The mounted plugins live outside this repo.** These scenarios mount
  `C:/Users/grima/Documents/craft-collection/plugins/...` by absolute path rather than
  vendoring them into the bank. Their content tree_sha enters `config_hash`, so the run
  is *pinned*, but it is not *reconstructible* from this repository alone.
- **One repeat, two tiers, one strategy, one effort.** Single-session, effort medium; the
  strong tier was not run.
- **Outcome-only.** Whether any arm actually loaded a skill — the recall axis the injected
  content is meant to move — is not instrumented in this bank.
- **Estimated USD, not billed USD** (STATUS D2).

## Related

- Companion banks from the same run: `2026-07-23-e1-debug-findings.md`,
  `2026-07-23-e1-data-findings.md`. Content A/B on a larger bug-fix bank:
  `2026-07-23-inject-content-v1-findings.md`.
- Ledger: `ledger/e1-verif.jsonl` (16 trial rows + 16 run rows, append-only). Regenerate
  the scorecard with `uv run fathom report e1-verif`; `report/` is gitignored.
- A later re-run of the same three banks under a different arm structure sits unreported
  in `ledger-rg2x2/` + `streams-rg2x2/` and is **not** covered here.
