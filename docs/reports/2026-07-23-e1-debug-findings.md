# Does injecting dispatch candidates change root-cause debugging behavior? — e1-debug findings

- **Date:** run 2026-07-23 (ledger committed the same day, `11e6447`, merged `86e7060`);
  report 2026-08-11. Bank: `e1-debug` (2 weak-footprint debugging tasks with a latent
  second defect site). One of three per-discipline banks in the same experiment —
  companions `2026-07-23-e1-data-findings.md` and `2026-07-23-e1-verif-findings.md`.
  Written from the committed ledger and the regenerated scorecard; `docs/STATUS.md`
  carried the bank as **Unreported**.
- **Question (operator):** does injecting concrete dispatch candidates into the system
  prompt change the *outcome* of a debugging task — specifically, whether the agent
  repairs the shared root cause instead of patching only the symptom it was told about —
  and does that depend on model tier?

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
| `oracle` | names the one right discipline for this bank (root-cause-first debugging) and paraphrases what it directs — the upper bound of a perfect semantic router |
| `registry` | the full static list of ~19 installed skills with one-line "when each applies" |
| `classifier` | what an offline prompt-classifier would emit: two ranked candidates for this prompt |

**Tasks** — each has a reported defect site named in the instruction and a latent second
site that shares the same underlying cause, never mentioned:

- `fix-pager` — reported `page_numbers` under-counts pages; latent `has_page` rejects the
  real last page. A local patch to `page_numbers` leaves `has_page` broken; a fix to the
  shared page-count math repairs both.
- `fix-slugify` — reported `slug` leaves stray punctuation; latent `anchor_id` produces
  dirty ids from the same tokenizer.

The verifier emits `reported_site_fixed` (the correctness gate), `second_site_fixed` (the
discriminating proxy for root-cause behavior) and `both_sites_fixed`.

## Result

| Arm | Pass | Pass rate | Wilson 95% CI | K | Infra errors |
|---|---|---|---|---|---|
| `bare-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `oracle-haiku` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |
| `registry-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `classifier-haiku` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `bare-sonnet` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `oracle-sonnet` | 1/2 | 50.0% | [9.5%, 90.5%] | 2 | 0 |
| `registry-sonnet` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |
| `classifier-sonnet` | 2/2 | 100.0% | [34.2%, 100.0%] | 2 | 0 |

**The per-criterion view collapses this to a single question asked once per arm.**

| Criterion | Result |
|---|---|
| `reported_site_fixed` | **100% in all eight arms (16/16 trials)** — every trial fixed what it was told about |
| `second_site_fixed` | the only discriminating criterion; identical to `both_sites_fixed` in every trial |

- **The correctness gate is saturated.** No arm ever failed the reported site. Everything
  this bank measures is the latent-site proxy.
- **The proxy is carried by exactly one task.** `fix-pager` passed in all eight arms
  (16/16 including its second site); every failure in the bank is `fix-slugify`'s
  `second_site_fixed`. Arms that repaired the shared tokenizer: `oracle-haiku`,
  `classifier-sonnet`, `registry-sonnet`. Arms that patched only `slug`: `bare-haiku`,
  `bare-sonnet`, `classifier-haiku`, `oracle-sonnet`, `registry-haiku`.
- **So the effective design is 8 arms × 1 discriminating trial each.** Every arm's score
  is one Bernoulli draw. Three of eight came up heads, and they do not line up with any
  content ordering: the perfect-router `oracle` arm succeeded at the weak tier and failed
  at the mid tier; `bare` failed at both.

### Economy

| Arm | Est. USD | Turns | Mean out-tok | Mean wall (s) |
|---|---|---|---|---|
| `bare-haiku` | $0.148 | 18 | 1,550 | 29.3 |
| `oracle-haiku` | $0.149 | 17 | 1,506 | 30.5 |
| `registry-haiku` | $0.134 | 15 | 1,398 | 24.8 |
| `classifier-haiku` | $0.183 | 25 | 2,047 | 37.4 |
| `bare-sonnet` | $0.683 | 13 | 1,151 | 22.9 |
| `oracle-sonnet` | $0.523 | 13 | 1,224 | 26.9 |
| `registry-sonnet` | $0.526 | 13 | 1,041 | 21.9 |
| `classifier-sonnet` | $0.732 | 14 | 1,380 | 24.6 |

Bank total **$3.08 estimated, 128 turns, 7.3 min** of summed trial time — $0.61 across
the eight haiku trials and $2.46 across the eight sonnet trials, a ~4× tier cost ratio
for no measurable quality difference in this bank. Injecting the ~2 kB `registry` block
did not raise cost at either tier; if anything it was the cheapest content arm. USD is
the adapter's token×price estimate under subscription auth (STATUS D2).

### The cross-bank pooling this run's decision actually rested on

The commit message reports a pooled figure, not this bank's. Pooling the identical arm
structure across all three `e1-*` banks gives n=6 per (content × tier) cell:

| Tier | `bare` | `oracle` | `registry` | `classifier` |
|---|---|---|---|---|
| haiku | 4/6 | 4/6 | 4/6 | 3/6 |
| sonnet | 2/6 | 3/6 | 4/6 | 6/6 |

The pre-registered kill gate keyed on the weak-tier cell: `oracle` (the upper bound of a
perfect router) tied `bare` at 4/6, Fisher p = 1.0. The unexpected mid-tier gradient runs
the other way — `bare` 2/6 to `classifier` 6/6, Fisher p = 0.061, which does not clear
0.05 and rests on 24 trials spread over three different banks and six different tasks.

## Verdict

**On this bank, nothing separates the arms.** The correctness gate is saturated at
16/16, the discriminating proxy resolves to one trial per arm on one task, and the three
successes are scattered across content arms and tiers in a pattern with no ordering —
the perfect-router arm won at the weak tier and lost at the mid tier.

What this bank does establish, narrowly:

1. **The instrument works as designed.** The reported-site/latent-site construction
   produces a proxy that a capable model fails often enough to be observable: 5 of 16
   trials patched only the symptom, and the pattern is a real behavioral distinction, not
   a verifier artifact.
2. **`fix-slugify` discriminates; `fix-pager` does not.** Sixteen trials all repaired
   `has_page` along with `page_numbers` — the shared page-count math is apparently hard
   to patch locally. Any future version of this bank should keep the slugify shape and
   replace or re-author the pager task.
3. **It does not establish anything about injected dispatch content.** Not a benefit, not
   harm, not equivalence. One draw per arm cannot rank eight arms.

## Limitations

- **Power is the binding constraint, and it is severe. n=2 per arm — 2 tasks × 1 repeat
  — over 8 arms, 16 trials in total.** With n=2 the Wilson interval for a perfect arm is
  [34.2%, 100.0%] and for a half-passing arm [9.5%, 90.5%]; every arm's interval contains
  every other arm's point estimate. **No arm ordering in this bank is distinguishable
  from noise**, and none should be quoted as a finding. This is not a directional result
  that needs more data to firm up — it is one coin flip per arm.
- **Effectively n=1.** Because `reported_site_fixed` and `fix-pager` are both saturated,
  each arm's score is decided by a single trial (`fix-slugify`). Eight one-trial arms.
- **The pooled cross-bank reading is thin too.** n=6 per cell, and it pools three banks
  with different disciplines, different tasks and different verifiers as though they were
  repeats of one experiment. The weak-tier tie (4/6 vs 4/6) is a legitimate basis for a
  pre-registered *stop* decision — a gate that fires on "no lift observed" is a valid
  decision rule — but it is not a demonstration that injection has no effect. The
  mid-tier gradient (2/6 to 6/6, p = 0.061) is at best a hypothesis; the commit message
  correctly calls it underpowered.
- **The mounted plugins live outside this repo.** These scenarios mount
  `C:/Users/grima/Documents/craft-collection/plugins/...` by absolute path rather than
  vendoring them into the bank (as `inject-content-v1` does). Their content tree_sha
  enters `config_hash`, so the run is *pinned*, but it is not *reconstructible* from this
  repository alone.
- **One repeat, two tiers, one strategy, one effort.** Single-session, effort medium.
  Nothing here transfers to other strategies or to the strong tier, which was not run.
- **Outcome-only.** The verifiers score the finished workspace. Whether any arm actually
  loaded a skill — the recall axis the injected content is meant to move — is not
  instrumented in this bank.
- **Estimated USD, not billed USD** (STATUS D2).

## Related

- Companion banks from the same run: `2026-07-23-e1-data-findings.md`,
  `2026-07-23-e1-verif-findings.md`. Content A/B on a larger bug-fix bank:
  `2026-07-23-inject-content-v1-findings.md`.
- Ledger: `ledger/e1-debug.jsonl` (16 trial rows + 16 run rows, append-only). Regenerate
  the scorecard with `uv run fathom report e1-debug`; `report/` is gitignored.
- A later re-run of the same three banks under a different arm structure sits unreported
  in `ledger-rg2x2/` + `streams-rg2x2/` and is **not** covered here.
