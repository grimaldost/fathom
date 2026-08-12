# T1: what a routing decision costs, and whether the rubric changes one

**Bought 2026-08-12. 54 trials, 53 completed, $14.04.** Bank `routing-decision-v1`,
arms `scenarios/routing-decision/`, ledger `ledger/routing-decision-v1.jsonl`,
analysis `tasks/routing-decision-v1/analyse.py`. Design of record:
[`docs/specs/2026-08-12-routing-mechanism-eval-design.md`](../specs/2026-08-12-routing-mechanism-eval-design.md).

## The headline, and it is not a single number

**The pre-registered stop rule fires at two of three deciding tiers.** `rubric` versus
`none` on the nine-brief block, modal route per brief across three repeats:

| deciding tier | agreement | Wilson 95% | verdict |
|---|--:|---|---|
| weak | **5/9** | [0.27, 0.81] | continue — the rubric changes 4 decisions |
| mid | **8/9** | [0.56, 0.98] | **STOP** — settled on decision cost |
| strong | **9/9** | [0.70, 1.00] | **STOP** — settled on decision cost |

Where the stop rule fires, C(m)'s execution and retry terms are identical between the
two mechanisms by construction — the tiers chosen are the same — so the comparison
reduces to decision cost, which T1 measured directly. **No outcome table is needed to
settle those two tiers, and none was bought.**

Reporting this as one pooled number would destroy the result. The rubric is *pure
overhead* exactly where it is most expensive to run, and *does the most work* exactly
where it is cheapest.

## Measured decision cost

Per-task USD, fitted from the K=1 and K=9 blocks (three repeats, medians):

| deciding tier | K | rubric premium over `none` | break-even correction rate (p_weak 1.0 / 0.8 / 0.7) |
|---|--:|--:|---|
| weak | 1 | $0.0199 | 7.6% / 9.2% / 10.3% |
| weak | 9 | **$0.0021** | **0.8% / 1.0% / 1.1%** |
| mid | 1 | $0.0748 | 28.6% / 34.6% / 38.6% |
| mid | 9 | $0.0331 | 12.7% / 15.3% / 17.1% |
| **strong** | **1** | **$0.2026** | **77.6% / 93.8% / 104.7%** |
| strong | 9 | $0.0172 | 6.6% / 8.0% / 8.9% |

**At the strong deciding tier, one decision at a time, the break-even exceeds 100% once
the weak tier's real pass rate drops to 0.7.** Above 100% means the rubric cannot pay
for itself at *any* correction rate: taking the decision costs more than the entire
strong-to-weak execution saving it could possibly unlock. And at that same tier it
changed **zero** of nine decisions.

The premium spans **two orders of magnitude** across deciding tiers — $0.0021 at
weak/K=9 against $0.2026 at strong/K=1. Where the decision is taken and how many tasks
it covers dominate everything else about this mechanism.

## The disagreements are one-directional

Every disagreement, at every deciding tier, is the rubric routing **up**:

| deciding tier | disagreements | rubric up / down | extra execution |
|---|--:|---|--:|
| weak | 4 | **4 / 0** | **+$0.0580/task** |
| mid | 1 | 1 / 0 | +$0.0124/task |
| strong | 0 | — | $0.0000/task |

The four at the weak deciding tier: `feature-ndjson-merge` (weak→mid),
`fix-decimal-round` (weak→mid), `refactor-dedupe-validators` (mid→strong),
`fix-ledger-replay` (mid→strong).

**This reframes the whole question.** At the weak deciding tier the rubric's decision
premium is $0.0021/task, but its *upgrade bias* costs $0.0580/task in extra execution —
**28x more**. So the rubric's cost is not in running it; it is in what running it makes
you buy. Whether that spend is justified turns entirely on whether those four upgrades
are necessary, which is exactly the `cheapest_adequate_tier` question.

The rubric is therefore not "expensive to consult" at the cheap end. It is
**systematically more conservative than unaided judgment**, and conservatism is what
costs money.

## Presentation moved the route more than the mechanism did

`fix-clamp2` is the one brief present in both blocks. **Six of nine arms routed it
differently at K=1 than at K=9** — and every flip ran the same way, `mid` alone →
`weak` in the batch:

```
none-strong  mid -> weak      shortcuts-weak    mid -> weak      rubric-weak    mid -> weak
shortcuts-strong mid -> weak  rubric-mid        mid -> weak      rubric-strong  mid -> weak
```

Mechanism made no difference to whether it flipped; `none`, `shortcuts` and `rubric` all
did. A task shown alone reads as harder than the same task shown beside eight others —
a relative-judgment effect, not a property of any policy.

**This is a finding about the problem, not about this rubric**, and it bounds what *any*
routing mechanism can achieve: if presentation context moves the answer for two thirds
of arms, a mechanism's accuracy is not a property of the mechanism alone. It also means
batch routing and per-spawn routing are not interchangeable — they produce different
answers on the same task. Recorded at n=3 on one brief; it deserves a wider test before
being leaned on.

## A method finding: a modelled decision cost is not evidence

The forward token model predicted `none-strong` at K=1 would cost $0.085; it cost
**$0.298**. It predicted the rubric premium at strong/K=1 would be $0.0800; it was
**$0.2026**.

The miss is not a level error that cancels in a comparison — **it is 2.8x on the
contrast itself**, which is the only quantity C(m) turns on. Decision cost is the term
that decides this study, so a modelled decision cost cannot stand in for a measured one,
and the earlier projection should be read as having established the *shape* of the
answer (tier-dependence, batch amortisation) and none of its magnitudes.

It also vindicates buying the cheap tranche first: the estimate was wrong in a way only
the purchase could reveal, and it cost $14 to find out rather than $280.

## Instrument health

- **Cost audit ratio 0.9888.** The CLI priced these cache-aware, so the FATH-B57
  fallback never fired, and the independent recomputation in `routing.cost_from_usage`
  agrees with the CLI to ~1% across 54 trials. FATH-B57 remains latent, not active — and
  the recomputation is now cross-validated against a real run.
- **One errored trial**: `rubric-strong` / `route-9-mixed` / repeat 2, `API Error: 529
  Overloaded` — a transient server-side fault, not a measurement failure. That single
  cell rests on n=2; every other cell has n=3. It was not re-bought, because the
  strong-tier result (9/9 agreement, zero disagreements) does not turn on it.
- **Arming verified live** on all six treatment arms: `rubric.md` 24,959 bytes and
  `shortcuts.md` 1,751 bytes each observed in the real spawn argv.
- **Smoke 7/8**, only `engine-boundary` red — the documented permitted failure.
- Spend: $14.04 recomputed / $14.20 as reported by the CLI, against a $4.73 forecast.

## What this settles, and what it does not

**Settled, no further spend required:**

- At the **mid and strong deciding tiers**, the rubric changes 8/9 and 9/9 decisions not
  at all, while costing $0.075 and $0.203 more per decision at K=1. It is pure overhead
  there. This is the common case — the dispatching session is usually the expensive one.
- The structural recommendation is now **measured rather than projected**: take the
  routing decision at the weak tier, and batch it. Both legs are confirmed — the premium
  is smallest there ($0.0021/task at K=9, a 1% break-even) *and* that is the only place
  the mechanism changes any decisions.

**Not settled:**

- At the **weak deciding tier** the rubric changes 4 of 9 decisions, all upgrades, worth
  +$0.0580/task in execution. Whether that is money well spent needs
  `cheapest_adequate_tier` for those four briefs. Nothing in T1 can answer it.
- Whether the rubric's routing is *better* anywhere. T1 measured what each mechanism
  emits and what emitting it costs — never whether the emitted tier was right.
- `shortcuts` versus `rubric` on quality. They disagree substantially (4/9 at mid, 5/9
  at strong), and `shortcuts` is consistently cheaper to run, but which routes better is
  the same unanswerable question.
- The presentation-context effect, beyond one brief.

## Recommendation on the substrate's $40 + $240

**Yes, still needed — but the question has narrowed enough that the full core looks like
an overbuy.**

T1 eliminated two of three deciding tiers and reduced the open question to: *are the
rubric's four upward corrections at the weak deciding tier necessary?* That needs
`cheapest_adequate_tier` for four briefs — `feature-ndjson-merge`, `fix-decimal-round`,
`refactor-dedupe-validators`, `fix-ledger-replay` — and only across the tier pairs the
disagreements actually span (weak-vs-mid for two, mid-vs-strong for two).

That is roughly **4 of 9 tasks and 2 of 3 tiers — about 30% of the core's cells**. The
$40 control should still be bought in full: it is what makes a null interpretable, and
T1 gives no reason to trust a saturated bank any more than before.

So the proposal, in the same cheap-first spirit that made T1 worth buying: **$40 control,
then a targeted ~30% slice of the core**, and the remaining 70% only if the slice leaves
the answer open. The substrate owner should price the slice — the 30% figure is inferred
from cell counts, not from their design.

If the owner would rather have the complete calibration table for its own sake, the full
core is defensible on those grounds. It is not required to answer the routing question
T1 was bought to close.
