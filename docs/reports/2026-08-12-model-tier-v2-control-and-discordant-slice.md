# model-tier-v2 — the control, and the four briefs where the mechanisms disagree

**Date:** 2026-08-12 · **Bank:** `model-tier-v2` (dataset_version 2) · **Spend:** $27.60 over
89 trials · **Ledger:** `ledger/model-tier-v2.jsonl` (160 rows, sha256
`040a9f8a1b9a218cf107dd1b140dc9923318787ef3ef10f2c0d892067febba33` after LF normalisation)

Buys: **T0** the positive control (20 trials) and a **targeted slice** of the discordant core
(60 trials) — the four briefs where the routing programme measured `rubric` and `none`
choosing different tiers. **T2 (census) and T3 (robustness) were not bought**, on the reasoning
in *What to buy next* below.

---

## 1. The finding that should be read first

`refactor-dedupe-validators` scores **45**. The rubric's own arithmetic maps 45 to **`mid`**.
The routing programme recorded `rubric-weak` — a weak model applying the rubric — choosing
**`strong`**.

**That over-escalation is not the points system's output. It is a cheap decider misapplying
it.** The distinction is load-bearing, because the obvious conclusion from the mid↔strong
result below is "the rubric over-provisions, delete the scoring" — and deleting the scoring
would remove something that had said `mid`. The `strong` came from the application, not the
formula.

Set beside the routing programme's own result — that a *strong* model applying the rubric
lands on the same tier as a strong model with no rubric at all — the coherent reading is:

> **the scoring is redundant where the decider is capable, and misapplied where the decider is
> cheap.**

No number of additional calibration cells tests that. A decider-capability experiment does.

## 2. The control: the ladder separates

| arm | draws | rate | 95% CI | gate-caught | silent |
|---|--:|--:|---|--:|--:|
| `haiku` | 1/10 | 0.10 | [0.02, 0.40] | 0 | 9 |
| `opus5` | 10/10 | 1.00 | [0.72, 1.00] | 0 | 0 |

One-sided Fisher exact **p = 5.95e-05** against α = 0.05, at the pre-registered
`min_repeats = 10`. **Separates.** Every downstream reading in this bank is therefore
interpretable: a null here would be a null about routing, not a bank without headroom — which
is exactly what `model-tier-v1` could never establish.

**Method finding: the verbatim-ported prior did not transfer.** `control-nonlocal-parse` is
`model-tier-v1`'s `fix-nonlocal-parse` copied letter for letter — same instruction, same
fixture, same two hard criteria — precisely so its recorded gradient would carry over. Its v1
record was `haiku` 2/5 (0.40). It came back **1/10 (0.10)**. The direction held and the
separation strengthened, so the gate verdict is safe, but the pre-registered power calculation
was sized against 0.4 and that rate no longer holds. **A historical pass rate is not a usable
prior for sizing power, even under letter-for-letter copying.** Here the error errs toward more
power than needed; the same error in the other direction buys an underpowered block that looks
adequate on paper.

## 3. The four discordant briefs

`none` and `rubric` are the tiers the routing programme observed each mechanism choosing at the
weak deciding tier. Adequacy bar **τ = 0.70**. `~` marks a non-robust point estimate.

### weak ↔ mid pair

| brief | weak | mid | strong | cheapest adequate | `none` | verdict |
|---|--:|--:|--:|---|---|---|
| `feature-ndjson-merge` (38) | **5/8** ‡ | 8/8 | 8/8 | **mid** `~` | weak | weak insufficient — escalation **correct** |
| `fix-decimal-round` (54) | **0/5** | **0/5** | 5/5 | **strong** `~` | weak | weak insufficient — **and so was the rubric's own choice** |

### mid ↔ strong pair

| brief | weak | mid | strong | cheapest adequate | `none` | rubric chose | **whose error** | verdict |
|---|--:|--:|--:|---|---|---|---|---|
| `fix-ledger-replay` (71) | **5/5** | 4/5 | 5/5 | **weak** `~` | mid | `strong` (formula: **strong**) | **the formula** | mid sufficed — escalation **unnecessary** |
| `refactor-dedupe-validators` (45) | **5/5** | 5/5 | 5/5 | **weak** `~` | mid | `strong` (formula: **mid**) | **the decider, not the formula** † | mid sufficed — escalation unnecessary, **but see †** |

> **† This row does not indict the points system.** `refactor-dedupe-validators` scores 45 and
> the rubric's formula maps that to **`mid`** — the same tier that turned out adequate. The
> `strong` came from a *weak model applying* the rubric and overshooting its own arithmetic
> (§1). Read in isolation this row looks like evidence that the scoring over-provisions; it is
> evidence that a cheap decider misapplies it. Of the two mid↔strong data points, **only
> `fix-ledger-replay` is an error of the formula** — there the formula itself says `strong`
> (score 71) and `weak` sufficed.

**The two pairs answer in opposite directions, and the split falls cleanly by pair.** The
rubric was right to escalate off `weak` on both weak↔mid briefs, and the escalation off `mid`
was unnecessary on both mid↔strong briefs — where `weak` would in fact have sufficed. **But
"unnecessary escalation" and "the formula was wrong" are not the same claim, and only one of
the two mid↔strong briefs supports the second**: on `refactor-dedupe-validators` the formula
said `mid` and a weak decider overrode it (see †). So the count against the points system's
*arithmetic* on this pair is **1 of 2**, not 2 of 2. **Nothing is
pooled.** Four briefs, 2–2, and a single verdict over them would average away the structure
that is the actual result.

Held at measured strength:

- Every reading is a **non-robust point estimate at n=5** except `fix-decimal-round`'s `weak`
  and `mid`, which are **robust** (Wilson upper bound 0.43 < τ).
- `refactor-dedupe-validators` is **fully saturated** (5/5/5) and carries no boundary
  information beyond "weak suffices".
- `feature-ndjson-merge`'s deciding reading is **soft and stays soft** — see ‡ below. It was
  bought to 8 repeats specifically to settle it, and did not settle.

### ‡ The one reading bought to settle, which did not settle

`feature-ndjson-merge`'s `weak` arm was the only reading that could flip a verdict, so it was
extended from 5 to 8 repeats (9 new trials, $2.48). Result:

| | passes | rate | 95% CI | robust against τ=0.70? |
|---|--:|--:|---|---|
| first 5 repeats | 2/5 | 0.40 | [0.12, 0.77] | no |
| all 8 repeats | **5/8** | **0.62** | [0.31, 0.86] | **still no** |

**The verdict does not flip** — 0.62 is below τ, so `weak` remains inadequate and the rubric's
escalation on this brief stands. **But the reading did not become robust**, and the reason
matters more than the result: the extension was priced on the assumption that the observed 0.40
would hold, at which 3/8 would have bounded at [0.14, 0.69] and cleared. The rate came back
**0.62** instead — the three new trials passed 3/3.

At a true rate near 0.62, this reading **cannot be made robust at any affordable n**: the bound
crosses below 0.70 only around **n ≈ 200** on that single arm. The tier sits too close to the
bar. This is the pre-registered "marginal tier" limitation arriving in practice, and it is not
a funding problem — it is a statement that `weak` on this brief is genuinely borderline rather
than clearly inadequate.

**Method finding, and this is the second instance in one wave.** An observed pass rate was used
to size a block, and failed to reproduce — twice:

| | rate used for sizing | rate observed | direction |
|---|--:|--:|---|
| `control-nonlocal-parse` (ported verbatim from v1) | 0.40 | **0.10** | more separation than sized for |
| `feature-ndjson-merge` `weak` (own first 5 repeats) | 0.40 | **0.62** | less separation than sized for |

Once is a fluke; twice, in opposite directions, is a property of small-n rates. **A pass rate
measured at n≤10 is not a usable prior for sizing the next block** — not from a sibling bank,
and not from the same arm on the same task. Power calculations resting on one are resting on an
assumption. The first instance erred safe; the second bought 9 trials that did not deliver the
robustness they were bought for.

### `fix-decimal-round` is where the third arm paid for itself

The slice was bought at three arms rather than the two the tier pair strictly required. On this
brief `weak` 0/5 **and** `mid` 0/5 is the both-fail pattern a two-arm design cannot interpret —
mid-insufficiency and a floored task look identical. `opus5` at 5/5 resolves it: the task is
achievable, so this is genuine mid-insufficiency. The extra arm was decisive on exactly the one
brief that needed it.

It also breaks the pre-registered frame. The question was "did the tier `none` chose suffice? if
not, the upgrade was correct." Here `none` was wrong **and the rubric was wrong** — it escalated
in the right direction and **under-escalated**. Routing by the rubric would still have shipped a
failure, and a silent one. That is not scored as a rubric win.

## 4. The cost inversion — a trap for the next reader

Execution cost over the four briefs:

| mechanism | execution cost | vs oracle |
|---|--:|--:|
| oracle (perfect routing) | $1.650 | — |
| `rubric` | $1.428 | **−13%** |
| `none` | $0.803 | **−51%** |

**Both mechanisms come in under the oracle. This is not a saving.** They are cheaper because on
`fix-decimal-round` both under-provisioned into a **robust** failure and simply never paid for
the `strong` tier the task required. Cheapness bought by shipping wrong work is negative value
recorded as a discount.

**Any C(m) table that nets these against correctly-routed briefs will report a saving that does
not exist.** A mechanism's cost is only comparable against the others *at equal delivered
quality*; where quality differs, the cost column is not a ranking. Read the escape rate first,
then the cost.

## 5. Every failure was invisible

**89 trials · 63 passes · 26 failures · 0 gate-caught · 26 silent.**

Not one failure at any tier on any task was visible to the shipped test suite. Consequences:

- **A start-cheap-and-escalate mechanism has nothing to fire on.** Its retry term is not small,
  it is **structurally zero** on this bank's task shapes, and its apparent cheapness is bought
  entirely with escapes.
- **Routing errors do not self-correct.** While this holds, "cheap" means "ships wrong work
  undetected", and the marginal value of a better router is bounded by the fact that nothing
  notices when it is wrong.
- Any `C(m)` table crediting cheap starts **must print the escape rate beside the cost**, or it
  systematically flatters the mechanism least worth adopting.

This is a property of the displaced-cause task shapes in this bank, not of any routing policy.
It is the binding constraint on the whole comparison and it is not bought away with more cells.

## 6. What to buy next — priced, not bought

**Not T2 (census, $150) and not T3 (robustness, $240).** A census would sharpen the weak/mid vs
mid/strong boundary, but the boundary is not what blocks the decision. The two things that do —
the application-versus-arithmetic finding (§1) and the 23/23 invisibility (§5) — are not
answered by more cells.

The cheapest decision-relevant buy is **repeats on the four briefs already measured**, which is
the stated remedy for the n=5 limit:

| option | new trials | ceiling @ $2/spawn | expected @ $0.314/trial | what it settles |
|---|--:|--:|--:|---|
| **A — four briefs to 10 repeats** | 60 | $120 | ≈$19 | makes every "adequate" reading robust (n=10 with a perfect record clears τ at lower bound 0.722) |
| ~~B — `feature-ndjson-merge` to 8 repeats~~ | ~~9~~ | ~~$18~~ | **BOUGHT, $2.48** | did not settle — see ‡ |

**Option B was bought and is now closed out (‡).** It did not flip the verdict and did not
achieve robustness, because the rate moved from 0.40 to 0.62. Extending it further is **not**
recommended: robustness there needs n ≈ 200 on one arm. Option A remains available but buys
robustness only on readings that are already unambiguous.

Beyond either: the decider-capability experiment §1 argues for, which this bank cannot run.

## 7. What this still cannot settle

- **Decision cost.** Not measured here; every `C(m)` from this bank is a lower bound.
- **How often the mechanisms disagree on a real workload.** The four briefs are the enriched
  discordant set, so a per-disagreement figure cannot be converted into a per-session saving.
- **Any threshold move.** Requires robust readings (unbought) *and* the playbook's
  cross-distribution rule, which no single bank can satisfy.
- **Whether escalation recovers.** The arms are open-loop; with 0/23 failures gate-visible, this
  bank cannot observe a repair even in principle.
- **Magnitude on three of four briefs.** Non-robust at n=5, by design and as pre-registered.

## Provenance

Smoke gate **7/8** (engine-boundary only; the tolerated result — these arms are
`single-session`). `validate model-tier-v2 --strict` 45 pass / 0 fail / 0 warn / 0 unverifiable.
Paid-run lock taken and released per block (T0 22 min, chunk 1 45 min, chunk 2 35 min), released
before analysis each time. Ledger normalised LF and verified row-identical after each block —
**60 CR characters appeared on every block despite `*.jsonl text eol=lf`**, the trap that
produced a fake digest earlier in the wave; digests in the header are post-normalisation.

---

## Corrections

**2026-08-12, after first publication.** The §3 mid↔strong table originally carried a single
`verdict` column reading "escalation unnecessary" on both rows. That was accurate about the
*outcome* and misleading about the *cause*: on `refactor-dedupe-validators` the rubric's own
formula says `mid` (score 45), and the `strong` came from a weak model applying the policy and
overshooting it. §1 said so; the table did not — and the table is what gets read, quoted, and
carried into a backlog row.

Added: a `rubric chose` column showing the formula's answer beside the observed choice, a
`whose error` column, the † note, and the qualification that the arithmetic is implicated on
**1 of 2** mid↔strong briefs rather than 2 of 2.

Recorded rather than silently edited, because the failure being corrected is precisely a number
crossing a boundary with its meaning stripped off — the same shape as the `quality` /
`first_attempt_pass_rate` divergence earlier in this wave. A correction that hides itself
teaches the next reader nothing.

**2026-08-12, second correction.** Option B (§6) was bought after first publication: 9 trials,
$2.48, `feature-ndjson-merge` to 8 repeats. It did not flip the verdict and did not achieve the
robustness it was bought for. Added as ‡, together with the second instance of the
small-n-prior method finding. Totals updated to $27.60 / 89 trials; ledger digest re-stamped.
