# Routing mechanisms on trial for net value — design of record

**Status:** pre-registered, authored, unrun. $0 spent.
**Bank:** `routing-decision-v1`. **Arms:** `scenarios/routing-decision/`.
**Analysis:** `src/fathom/routing.py`, tested in `tests/test_routing.py`.

## The question

Not "does the `choosing-models` rubric route accurately". The owner's question is
narrower and harder: **is routing by a scored rubric cheaper, all in, than not doing
it.** A rubric that routes perfectly and costs more than it saves is a rubric to
delete. So the rubric is on trial for net value, and accuracy is only one input to
that verdict.

## The estimand, pre-registered

For each candidate routing mechanism `m`:

```
C(m) = decision_cost(m) + execution_cost(tier chosen by m) + retry_cost(m)

subject to   quality(m) >= quality(best) - delta
```

Winner is `argmin C(m)`. **Quality is a constraint, not the objective.** Every term is
measured or computed from measurements.

- **`delta` = 0.05** (5 percentage points of per-task P(correct)), pre-registered as
  primary; `delta = 0.02` reported alongside as a sensitivity. Both are stated now, in
  advance, so neither is chosen after seeing which one changes the answer.
- **Quality** is `P(the task ends correct)` after any detected retry — not "the first
  attempt passed". A mechanism that fails cheaply and repairs is not penalised for the
  failure; a mechanism whose failures are *not detected* is, because those are escapes.
- **Units.** C(m) is USD **per dispatched task**, so mechanisms are comparable across
  episode sizes.

### The asymmetry the design exists to see

The routing decision is taken by the session dispatching the work, and that session is
frequently expensive. A scored rubric can therefore be paying strong-tier prices to
decide that some downstream task deserves a weak-tier model. If the decision costs more
than the routing saves, the rubric is net-negative however well it routes.

So `decision_cost` is priced **at the tier the decision is actually taken at**, and
every mechanism is measured at all three plausible deciding tiers rather than one.
This is the single most load-bearing choice in the design.

## The mechanisms

| mechanism | decision rule | decision cost | measured or computed |
|---|---|---|---|
| `rubric` | the `choosing-models` skill as shipped — score on the rubric, map score to tier via the thresholds in `models.toml` | body + rubric + data file injected: ~3.8k words / ~6.1k tokens | **measured** (3 deciding tiers) |
| `shortcuts` | a floor plus a shape lookup, no scoring arithmetic (authored here; text below) | ~335 words / ~0.44k tokens | **measured** (3 deciding tiers) |
| `none` | no mechanism — whatever the dispatching session would do unaided. The true baseline | nothing injected | **measured** (3 deciding tiers) |
| `fixed-mid` | one tier for everything | zero by construction | computed |
| `always-weak-escalate` | start weak; escalate one tier when the gate fails | zero by construction | computed (retry term is the whole arm) |
| `classifier` | delegate the decision to a weak-tier call that emits a tier | the `weak` deciding-tier cells, plus one delegated spawn | computed from measured cells |

`classifier` earns its place without a tenth arm: it is exactly "`shortcuts` or
`rubric`, decided at the weak tier", and the grid already buys those cells. Treating it
as a composition rather than a new arm is what keeps the sixth mechanism honest.

### The `shortcuts` variant, in full

Authored for this study, and authored to *win if it can* — a strawman would make a
`rubric` victory meaningless. It deliberately encodes the same insight as the rubric's
cross-shape floor (coverage of the fix site, not breadth of the change) as a rule to
read rather than a score to compute. Verbatim text:
`scenarios/routing-decision/assets/shortcuts.md`. A test asserts it carries no scoring
arithmetic, because "no arithmetic" is its defining property rather than a stylistic
preference.

## Program 1 — decision cost and decision quality

**Bank `routing-decision-v1`.** The task *is the routing decision*: N briefs in, one
tier per brief out, written to `routing.json`.

**The briefs** are copies of `model-tier-v2`'s tasks, so the join to that bank's
outcome table is exact. Nine of them, spanning the six dispatch shapes the design
requires — authoring, refactor, debugging, data work, review, planning — and the
rubric score range 20 to 71. Provenance, scores and the known coverage shortfall:
`tasks/routing-decision-v1/provenance.toml`.

**Block sizes separate fixed from marginal decision cost.** Three single-brief blocks
(K=1) and one nine-brief block (K=9) give a two-point fit per (mechanism, deciding
tier). This matters more than it looks: a mechanism that loads a 6k-token policy pays
that once per episode, so a one-off spawn decision and a nine-task series-authoring
pass are *different economies*, and a study measuring only one would generalise a
number that does not generalise.

**What the verifier scores, and what it refuses to.** Hard criteria are
well-formedness only: an answer exists, covers every brief once, and names legal tiers.
Routing **accuracy is deliberately not a criterion** — its ground truth
(`cheapest_adequate_tier`) does not exist yet, and a bank that graded it would be
asserting an answer key rather than measuring one. Instead the verifier *records* the
emitted routing as `chose__<brief>__<tier>` booleans, which reach the ledger and are
rejoined at analysis time. Accuracy is therefore derived from evidence at both ends,
or not reported.

## Program 2 — the substrate (not mine)

`model-tier-v2`, in the `eval/tier-separating` worktree (PR #27), owes this study a
per-task table: `{task_id, rubric_score, per-tier outcome, per-tier cost,
cheapest_adequate_tier}`.

**Its current state, checked 2026-08-12: authored, unrun, $0 spent.** Its own README
records the block — `fathom smoke` returns 5/8 with `OAuth session expired`, so no
paid trial has been bought. `scores.toml` (rubric scores) exists and is complete for
all nine sampled briefs. **The outcome and cost columns do not exist**, and neither
does `cheapest_adequate_tier`.

The consequence, stated plainly: **the execution-cost and accuracy halves of C(m)
cannot be measured until that bank runs.** This design does not work around that by
substituting a guess; `Substrate.require` raises rather than inventing a row, and every
result carries `n_missing`.

### The coordination surface, and how the two halves compose

Merged 2026-08-12. `calibration.routing_substrate` emits the agreed artifact and
`Substrate.from_artifact` consumes it. The division of labour is explicit on both sides
and the two are complements, not duplicates:

| term | owner |
|---|---|
| `execution_cost`, `retry_cost`, `quality`, `cheapest_adequate_tier` | `calibration.mechanism_costs` (the substrate bank) |
| `decision_cost` | **this bank** — measured by running each mechanism |

Their `mechanism_costs` reports `decision_cost_usd` as `null` rather than `0` and calls
it "a different programme", so its `total_cost_usd` is a documented **lower bound**.
C(m) is complete only when the two are added. A test asserts that `null` contract, so
the day it silently becomes `0` this study finds out.

**One field is derived, not copied.** Their `gate_caught_failures` is a *count of
failures the gate caught*; `detect_rate` here is a *per-failure probability*. The
denominator is therefore `trials - passing`, not `trials`. Dividing by trials would
understate detection on a mostly-passing tier and quietly turn repairable failures into
escapes — which biases every mechanism that starts cheap. Pinned by a test.

**A divergence found by a cross-implementation test, now resolved.** Running both
implementations on the same fixture, the **cost terms agree exactly** — a strong
independent check on both. **The quality terms did not**: theirs 0.55, mine 0.70.

**Resolution, decided 2026-08-12: quality is measured POST-REPAIR.** If C(m) charges
the retry, the quality term must credit the repair that retry produces, or every
cheap-start-and-escalate mechanism pays twice — once in cost, once in an unearned
quality penalty. It is also what the work is for: a failure the gate caught and
repaired is *delivered correct*, at a price already on the books; an escape is not.
That is precisely why the `detect_rate` denominator (`trials - passing`, not `trials`)
is load-bearing, and its test stays.

So that neither programme owns the other's estimand:

- The substrate emits **raw facts only** — per tier: passes, failures, and how many of
  those failures the gate detected. Its mechanism-level field is being renamed
  `quality` -> `first_attempt_pass_rate`, because one name meant two things for a week.
- This module owns the derived estimand and names it **`quality_post_repair`**, with
  the derivation in code. `first_attempt_pass_rate` is reported alongside it, so the
  two quantities sit next to each other rather than in two documents.
- The cross-implementation test is now an **identity**, not a snapshot:
  `quality_post_repair = first_attempt_pass_rate + repair_credit`, with the credit
  recomputed from the raw per-tier facts. It fails if *either* side silently changes
  meaning — which a test pinning today's 0.55 and 0.70 would not catch. It reads
  either spelling, so the rename strengthens it instead of breaking it.
- The `decision_cost_usd is None` contract keeps its own test. A `null` that silently
  becomes `0` is the same failure class as a gate that cannot fail: it reads as a
  measurement when it is an absence.

### Two design elements leaning the same way — worth stating plainly

The quality definition is the **second** element found biasing in the same direction.
The first was the substrate's admission screen: dropping saturated rungs deletes
exactly the evidence of over-provisioning, which favours the dearer mechanism. The
quality definition understated exactly the mechanisms that start cheap and escalate,
which again favours the dearer mechanism.

Neither was deliberate and each had a defensible local rationale. That is the point:
**two independent elements leaned toward the incumbent**, and the direction is the one
that protects the thing under test from being retired. A study whose incidental design
choices all point one way should be read as having a thumb on the scale until each is
checked, so this section exists to make the pattern visible rather than to litigate
either choice. A third element leaning the same way should be treated as a finding
about the design process, not another local fix.

## The composition

`src/fathom/routing.py`. Given the substrate table and the measured decision costs, C(m)
is largely **computed** rather than separately bought: apply each mechanism's rule to
each task, look up the outcome and cost at the tier it chose, add its decision cost and
the retry the rule implies.

Three properties worth naming, each asserted by a test:

1. **The same retry machinery for every mechanism.** A failure buys a retry only if the
   gate detects it; an undetected failure is an escape that costs nothing more and
   removes the quality instead. This is what stops a cheap tier from looking free, and
   it is why `always-weak-escalate` is evaluated on the substrate's own detection rates
   rather than an assumed retry rate.
2. **Cost is recomputed from raw usage, not read from `cost_usd_est`.** Under
   subscription auth the CLI reports `total_cost_usd == 0` and fathom's fallback prices
   only the uncached `input_tokens` field — 48 tokens on a trial that actually read
   548k from cache. That failure would understate a large cached system prompt by two
   orders of magnitude, which is *precisely the arm under test*. `audit_ledger_costs`
   surfaces the disagreement rather than silently correcting it.
3. **Every headline is reported per task mix.** A mechanism that wins on a bank of hard
   tasks can lose on a realistic session mix. Mixes are named hypotheses, never
   measurements — nothing here observed the real distribution of task shapes — so the
   decision-relevant output is `break_even_hard_fraction`: the share of hard work above
   which a mechanism starts paying for itself.

## Priced tranches, in buy order

Prerequisite, $0: **host re-authentication, then `fathom smoke` must pass.** A human
step. Nothing below is buyable until it does.

Per-spawn cap `--max-budget-usd 2` throughout. Expected totals are from the forward
token model (`routing.TokenModel`, pinned in `TestPrePurchaseProjection`); the $2 cap
times 180 trials gives a $360 hard ceiling, which is 26x the expectation and is a rail,
not a forecast. Every tranche is resumable — the resume key skips completed trials, so
a mid-run token expiry costs nothing but a re-invocation.

| # | what | trials | expected | makes decidable | stop rule |
|---|---|---|---|---|---|
| **T1** | 9 arms x {`route-1-mechanical`, `route-9-mixed`} x 3 repeats | 54 | **$4.73** | `decision_cost(m)` split into fixed and marginal, at all three deciding tiers; and the **inter-mechanism agreement rate** | If `rubric` and `none` agree on >=8/9 briefs, the rubric's routing value is bounded by one disagreement and the comparison is already settled on decision cost alone — **stop; do not buy T2 or T3 for this question.** |
| **T2** | + {`route-1-review`, `route-1-ledger`} x 9 arms x 3 repeats | 54 | **$3.69** | whether decision cost varies by brief shape, and whether disagreement concentrates on hard briefs | If K=1 cost is flat across the three single blocks (CV < 15%) **and** agreement is uniform across shapes, drop the extra single blocks from T3 and buy repeats only on `route-1-mechanical` + `route-9-mixed`. |
| **T3** | repeats 3 -> 5 on all 4 blocks | 72 | **$5.61** | per-mechanism routing distributions at usable precision (Wilson intervals on agreement) | If the 3-repeat intervals already separate the mechanisms' decision costs and no mechanism's routing is unstable across repeats, T3 buys precision nobody needs — skip it. |
| **T4** | **the substrate** — `model-tier-v2`'s matrix | not mine | not mine | `execution_cost`, `retry_cost`, `quality`, and the accuracy join | Not mine to stop or start. Without it C(m) stays a projection, and this design says so rather than filling the gap. |

**Full Program 1 at repeats=5: 180 trials, expected $14.03.**

### How a tranche is actually invoked

`--limit` cannot select a tranche: it truncates a **scenario-major** comprehension
(`for scenario, for task, for repeat`), so capping it drops whole arms rather than whole
blocks. `--tasks` is the flag for this, and it names the blocks directly:

```sh
uv run fathom run routing-decision-v1 \
    --scenarios-dir scenarios/routing-decision \
    --tasks route-1-mechanical,route-9-mixed \
    --repeats N --max-budget-usd 2
```

This is safe against the resume key, `(bank, dataset_version, task_id, config_hash,
repeat)` — **the task set does not enter it** — so a tranche appends to the same ledger
and a later full-bank invocation resumes over it rather than re-buying it.

Chunk by **raising `--repeats` one at a time** (1, then 2, then 3) rather than by
splitting arms: each invocation adds one complete repeat layer across every arm, so an
interruption always leaves a balanced design rather than a matrix with some arms deeper
than others. Every chunk re-runs the free bank validation and the arming pre-flight.

## The projection from existing numbers

**Labelled as a projection, not a result.** Decision costs come from the forward token
model; execution costs are `model-tier-v1` ledger medians (35 trials/arm) mapped to the
current lineup by ascending cost — a *different, saturated* bank, so they carry the
shape of real agentic coding work but not this bank's difficulty.

Observed per-task execution cost: weak $0.076, mid $0.225, strong $0.337. One
strong-to-weak correction therefore saves $0.261; one mid-to-weak saves $0.150.

The rubric's decision-cost premium over `none`, and the correction rate it must achieve
to pay for itself:

| deciding tier | K | premium/task | break-even, strong->weak | break-even, mid->weak |
|---|--:|--:|--:|--:|
| weak | 1 | $0.0160 | 6.1% | 10.7% |
| weak | 9 | $0.0030 | 1.2% | 2.0% |
| mid | 1 | $0.0480 | 18.4% | 32.1% |
| mid | 9 | $0.0091 | 3.5% | 6.1% |
| **strong** | **1** | **$0.0800** | **30.6%** | **53.4%** |
| strong | 9 | $0.0152 | 5.8% | 10.1% |

**The reading.** In the worst and entirely ordinary case — one spawn decision at a
time, taken by an Opus session — the rubric must improve on unaided judgment for
roughly **one decision in three** (if every correction is a full strong-to-weak move) or
**one in two** (for mid-to-weak). That is a demanding bar, and the existing calibration
evidence does not suggest the rubric clears it: three model-tier calibration runs put
the on-diagonal count at 1/7, and while the honest reading there was "the bank had no
headroom" rather than "the rubric is wrong", nothing on record shows the rubric
correcting a third of decisions.

The same table carries the constructive half, and it is the more useful finding: the
premium is driven by **where the decision is taken and how many tasks it covers**, not
by the rubric's content. Deciding at the weak tier cuts the bar 5x; batching nine tasks
cuts it 5x again; doing both cuts it 25x, to about 1%. If the measurement confirms
this shape, the actionable change is not "delete the rubric" but "stop paying Opus
prices to run it one task at a time" — and that change is available whichever way the
accuracy question lands.

## What this design still cannot settle

1. **Anything requiring the substrate.** Execution cost, retry cost, quality, and
   routing accuracy all wait on `model-tier-v2`. Until then C(m) is a projection with
   one measured term.
2. **Whether the rubric is *accurate*.** This design measures what routing each
   mechanism emits and what that emission costs. Whether the emitted tier is the right
   one is Program 2's question, and it inherits Program 2's known weakness: the weak
   band holds one task, so "the weak tier suffices for trivial work" will be a K=1
   claim that repeats cannot fix.
3. **A 5-point quality non-inferiority.** With 9 briefs and 5 repeats the design is
   powered to separate **costs** (large, low-variance, and mostly deterministic given
   token counts) but almost certainly **not** to certify `delta = 0.05` on quality. If
   the run cannot distinguish two mechanisms' quality at any affordable n, the report
   will say exactly that rather than record a null as equivalence.
4. **The in-session cost of a loaded policy.** A fresh fathom spawn is not a long
   session. Once the rubric is in a real session's context it is re-read on every
   subsequent turn, for the rest of that session — a tax this bank does not observe and
   that makes the measured decision cost a **lower bound** on the real one. The
   direction is known (it can only make the rubric dearer); the magnitude is not.
5. **The real task mix.** No part of this study observed how a working week's dispatched
   tasks are distributed across shapes and difficulty. Every mix is a hypothesis, which
   is why break-even is reported rather than a single headline.
6. **Whether a human would route better than any of these.** Not an arm, not measured,
   and worth naming because "the author just picks" is the mechanism actually in use
   most of the time.
