# Tier-separating calibration bank + model×oracle-quality crossing — design

- **Status:** authored 2026-07-14. Bank **not yet built and not yet run** — this
  is the design of record for the fix the recalibration playbook flags as its
  "known limitation" (§ *Known limitation & the standing high-leverage fix*). The
  paid matrix run is deferred and needs separate budget approval (ADR-0007 cost
  rails; playbook § *Deferred: the efficiency study*).
- **Extends:** [`2026-06-16-fathom-model-tier-calibration-design.md`](2026-06-16-fathom-model-tier-calibration-design.md),
  ADR-0007 (model-tier calibration); the oracle-quality factor this design adds — a
  new experimental dimension, not a lineup refresh — is recorded in **ADR-0008**,
  which must be accepted before build. Consumes the `calibration.py` arm-resolution
  generalization landed 2026-07-14 (family-token → tier, no fixed arm list), so new
  models and tiers land on the ladder without a code change — **but the oracle axis
  is a new factor `calibration.py` does not yet model** (see Part C and the
  acceptance criteria; wiring it is a build task, not something the arm-resolution
  work already satisfies).
- **Downstream:** settles the *oracle-coverage discount* that ships as a **labeled
  hypothesis** in `humblepowers:choosing-models` (its `models.toml` provenance and
  SKILL doctrine both say the downshift is licensed by oracle coverage, not gate
  presence — untested until this bank runs).

## Problem

`model-tier-v1` **over-saturates**: 6 of 7 scored tasks are aced by every tier, so
the entire tier calibration rests on one *separating* task, `fix-nonlocal-parse`.
Crucially, that is the sole task that **separates** — not the sole task of its
*shape*: v1's `fix-nonlocal-urlkey` is the same cross-module root-cause genre
(rubric 65 vs 67, near-identically scored) yet saturated — aced by Haiku where
parse needs Opus. So the separating shape is **necessary but not sufficient**; two
same-shape tasks landed on opposite sides of the tier line. That is the load-bearing
reason Part B screens each candidate *empirically* rather than trusting its shape.
Two more facts from the v1 record make the gap concrete:

1. **The rubric structurally avoids the mid/strong boundary.** The blind re-rating
   in `tasks/model-tier-v1/scores.toml` confirmed pre-mortem FM-3: the
   model-complexity rubric (the ported pr-prompt-scorer, now at
   `choosing-models/references/scoring-rubric.md`) clusters single-file bugfixes in
   the low-mid 30s–40s and jumps to ~61–67 for cross-module root-cause tasks, so it
   *brackets* the 55
   mid/strong edge (money 44 / nonlocal 65) but never sits on it. Boundary
   placement — the thing the study exists to locate — is under-determined.
2. **The effort sub-study had to collapse to one task.** `model-tier-effort` runs
   only `fix-nonlocal-parse`, because it is the one task with headroom (Haiku 40%
   / Sonnet 60% / Opus 100% on hard criteria); every other v1 task ceilings at
   100% and effort can move nothing.

Separately, `choosing-models` shipped an **oracle-coverage discount** — the claim
that the value of a verification gate tracks the oracle's *coverage and
independence*, not the gate's mere presence (ablation-v2: 8/8 gates green but 5/8
oracle escapes at the weak tier). It ships labeled a hypothesis because nothing in
the stack crosses model tier against oracle quality to test it.

So there are two gaps, and one bank can close both:

- **Gap A — separation.** Not enough tasks that *reliably* separate tiers at graded
  difficulty, and none that hit the 55 boundary.
- **Gap B — the oracle question.** No experiment that varies oracle quality while
  holding the task fixed, so "a stronger oracle licenses a cheaper model" is
  asserted, not measured.

## Goals / non-goals

**Goals.**
- A `model-tier-v2` bank whose tasks reliably separate weak/mid/strong at graded
  difficulty (not flaky), including rungs on the 25 and 55 boundaries.
- A **weak-model-fails screen** that admits a task to the bank only after cheap
  evidence that it separates — so the expensive matrix never runs on a task that
  saturates or is flaky.
- A **model × oracle-quality** crossing that turns the oracle-coverage discount
  from a hypothesis into a measured interaction.

**Non-goals.**
- Running the paid matrix (deferred; separate approval).
- Re-tuning the numeric thresholds. Thresholds move only on cross-distribution
  evidence (playbook Decision rule); this bank *produces* that evidence, it does
  not pre-judge it.
- Replacing `model-tier-v1`. v2 is additive; v1 stays as the historical baseline
  and its resume-keys are untouched.

## Part A — the tier-separating task set ("boundary + heterogeneity")

### The separating shape

The one v1 task that separates does so because of its *shape*, not its surface
difficulty: a **displaced-cause / cross-module** bug where the fault surfaces at
one call site but the root cause is shared by a second consumer. A weak model
patches the symptom site (the visible failing case) and leaves the second consumer
broken; a strong model fixes the shared root cause and both pass. The bank
generalizes that shape into a graded ladder rather than relying on one instance.

The shape is **necessary but not sufficient** — v1's `fix-nonlocal-urlkey` shares
it yet saturated (aced by Haiku). So the roster below is a set of *candidates* the
Part B screen must each prove separates empirically, not a set the shape alone
qualifies. The three variants and the graded ladder raise the odds that *enough*
candidates survive the screen, not the certainty that any given one will.

Three heterogeneous variants of the shape, so separation is not an artifact of a
single trick:

- **Displaced cause** — the fix must move upstream of the reported symptom (the v1
  `fix-nonlocal-parse` family).
- **Backend parity** — two implementations (e.g. an in-memory and a serialized
  path) must stay behavior-identical; a weak model fixes the one under test and
  skews the other.
- **Cross-module invariant** — an invariant enforced in module X is violated via
  module Y; the weak model adds a guard at the report site instead of restoring
  the invariant at its source.

### Roster (target, to be blind-scored and screened before build-out)

Each task ships, exactly as in v1: a pure-stdlib buggy package, a shipped test
suite that **passes on the buggy source** (does not cover the planted bug), and a
`verify.py` emitting a flat `{criterion: bool}` object with an easy **anchor**, one
or more **hard** (capability-gated) criteria at the *displaced* consumer(s),
`no_regression`, and `regression_test_present`.

| task | shape | band | target score | separation mechanism (hard criteria) |
|------|-------|------|-------------:|--------------------------------------|
| `fix-clamp2` | single-fn | low | ~12 | trivial; both tiers pass — anchors the weak floor |
| `fix-strip-unicode` | single-fn | low | ~22 | weak/mid **25 boundary** rung |
| `feature-ndjson-merge` | cross-module | mid | ~40 | second reader path must match the first |
| `fix-tz-window` | displaced-cause | mid | ~48 | DST edge at a second call site |
| `fix-decimal-round` | backend-parity | mid | ~55 | **55 boundary** rung: float and Decimal paths must agree |
| `fix-quota-rollup` | cross-module invariant | mid/high | ~58 | just-over-55 rung, brackets the edge from above |
| `fix-graph-cycle` | displaced-cause | high | ~66 | cycle detected at traversal, root cause in the builder |
| `fix-merge-3way` | cross-module | high | ~72 | conflict resolution must hold for a third, un-exercised input |
| `fix-ledger-replay` | backend-parity | high | ~78 | replayed and live aggregates must reconcile |

Spread gate (mirrors v1): ≥2 tasks per band; boundary rungs within ±5 of the 25
and 55 edges. The 55 edge — v1's gap — is deliberately double-covered
(`fix-decimal-round` at ~55, `fix-quota-rollup` at ~58). But there is a real tension
with the diagnosis above: the rubric *resists* scoring cross-module tasks near 55
(it clusters them at 61–67), and both 55-edge rungs use exactly that shape, so on
blind re-rating they are likely to drift UP out of the [50, 60] band. **Escape
hatch:** if, after one reshape pass, no candidate lands a blind score in [45, 60]
(the rubric's void), the bank ships with the 55 edge *bracketed* rather than *hit* —
v1's own honest limitation — and records it, instead of blocking the whole bank on a
rung the rubric may structurally refuse. The ≥2-per-band gate is likewise
best-effort: drift is not one-directional (a low single-file task at ~22 can drift
up into mid), so final band populations are settled by the blind scores, not
asserted here.

Scores above are **author targets**, not final. Final scores come from two blind
raters with the model-complexity rubric shipped at
`choosing-models/references/scoring-rubric.md` — the ported, pinned successor to
pr-prompt-scorer, the same rubric v1 used, kept pinned for cross-study continuity —
averaged into `scores.toml`, exactly as v1. The numbers here only size the ladder.

## Part B — the weak-model-fails screen (admission gate; "gap 0, not flaky")

A task earns a place in the bank only after a **cheap two-arm screen** proves it
separates — run *before* the full crossed matrix:

1. Run only the **weak** (Haiku) and **strong** (Opus) arms, at `standard` oracle
   (Part C), `--repeats 5`, on each candidate task. The two arms run as independent
   per-arm repeats — there is no cross-arm repeat pairing, so admission is stated on
   each arm's own rate, not on a joint per-repeat event.
2. **Admit** the task iff **every** repeat agrees: the anchor passes on all repeats
   of *both* arms (well-formed and reachable), the weak arm **fails ≥1 hard
   criterion on all 5 repeats**, and the strong arm **passes all hard criteria on
   all 5 repeats**. Unanimity, not a majority — a task that separates *reliably*
   must do so every time at this sample size.
3. **Reject** any task that is not unanimous: flaky (the weak arm passes the hard
   criteria on *any* repeat, or the strong arm fails them on *any* repeat),
   saturated (both pass), or broken (any anchor failure). The admission rule (2) and
   this rejection rule are exact complements — there is no repeat count that both
   admits and rejects. A rejected task is re-shaped once or dropped, never carried
   into the paid matrix.

This is the operational meaning of "reliably separate tiers at graded difficulty
(not flaky)". It costs 2 arms, not 9 cells, so a saturating task is caught for
~2/9 of a full-matrix task's spend. The screen result is recorded per task; the
bank's `README.md` reports the admitted set and the rejects with their failure mode
(saturated / flaky / broken), so the selection is auditable rather than asserted.

Mid (Sonnet) is intentionally **not** in the screen — separation is a
weak-vs-strong property; the mid arm's value is in the full matrix, where it places
the boundary.

## Part C — the model × oracle-quality crossed design

### Hypothesis

From `choosing-models`: **the value of a verification gate tracks the oracle's
coverage and independence, not the gate's presence.** If true, raising oracle
quality on a fixed task should catch a weak model's displaced-cause miss (forcing a
real fix or an honest fail) while a thin oracle waves the symptom patch through as
a false pass. The licensed downshift then depends on oracle quality — which is
exactly the discount `choosing-models` applies but has never measured.

### The crossing

**model tier** {weak, mid, strong} × **oracle quality** {thin, standard, strong},
the same nine tasks under all three oracles (the task code is fixed; only
`verify.py` / `[verify].hard_criteria` change):

- **thin** — anchor + the single symptom-site criterion. A patch at the reported
  failure passes.
- **standard** — the v1 contract: anchor + all hard criteria at the planted
  consumers + `no_regression` + `regression_test_present`.
- **strong** — standard + an **independent** adversarial check the symptom patch
  cannot satisfy: a hidden third consumer, a property/metamorphic test over the
  invariant, or a mutation probe on the root-cause site. "Independent" is the load
  bearing word — it must exercise the root cause through a path the task
  instruction never names.

Oracle quality is a **bank-level knob**, realized as three `verify.py` variants
selected by arm config. The model tier still resolves from the arm name's family
token, so a `haiku-thin` / `opus-strong` naming lands each arm on the *tier* ladder
without an edit — but the **oracle dimension does not resolve itself**, and naming
alone does not cross it. As-built, `calibration.py` has no oracle axis:
`arm_tier` reads only a model-family token, and `_tier_arm` keeps exactly **one arm
per tier** (`sorted(...)[0]`), so the three same-model oracle variants
(`haiku-thin` / `haiku-standard` / `haiku-strong`) all collapse to `weak` and only
one survives into the tier verdict / confusion / context layers. Crossing therefore
requires new code — an arm → (tier, oracle) resolver and a model×oracle interaction
estimator — specified as a build task in the acceptance criteria below, not implied
by the family-token resolution.

### What the matrix would show

The oracles are strictly nested (thin ⊂ standard ⊂ strong), so set inclusion alone
forces every tier's pass-rate to be **non-increasing** as oracle quality rises —
that much is a tautology, not the signal. The signal is the **model×oracle
interaction**: whether the *weak* tier's oracle-quality slope is materially steeper
than the *strong* tier's. Set inclusion constrains both slopes to ≤ 0 but says
nothing about their magnitudes or their difference — that is empirical.

- **If the hypothesis holds:** the weak tier's slope is steeply negative (its symptom
  patches get caught as the oracle sharpens) while the strong tier's is ≈ flat (it
  fixed the root cause, so a sharper oracle finds nothing new). `choosing-models`
  keeps the discount and can *calibrate* it against the weak slope.
- **If the interaction is null** (the weak and strong slopes are indistinguishable):
  oracle quality does not *differentially* license the weak tier, and the
  `choosing-models` oracle-coverage modifier should be **retired** (it ships labeled
  exactly so this result can retire it without a doctrine rewrite). The retirement
  condition is the **null interaction**, not "flat pass-rates" — the admission screen
  selects tasks where the weak arm already fails the `standard` oracle, so the weak
  thin→standard leg is non-flat *by construction* and cannot itself be the test.

**What this can and cannot conclude.** The crossing is **open-loop**: each cell grades
a fixed artifact post-hoc, with no repair step. It therefore measures oracle
*detection* — a sharper oracle catching a weak model's displaced-cause miss — and
reads that as the signal for the *licensing* claim (a sharper oracle making a cheaper
model adequate) only under the stated interpretation that detection-rate is what a
downshift should be gated on. Two honest limitations: (a) with no fix loop it cannot
show that the weak model, *confronted* with the sharper oracle, would then succeed —
only that the oracle would catch it; (b) the load-bearing `standard → strong` contrast
is **not** protected by the admission screen (which gates only thin/standard
separation), so on admitted tasks the weak arm already fails `standard`, and the
standard→strong leg can come back null for *measurement* reasons rather than because
the hypothesis is false. Mitigation: design each task's `strong`-oracle independent
check (Part C) to have real headroom over `standard` on the admitted tasks, or that
contrast is uninformative.

Either outcome is a real finding within those limits. The point of authoring the
crossing is that the current stack cannot produce *either* — it can only assert.

## Acceptance criteria (for the authored bank, before any paid run)

- Roster ≥9 tasks; ≥2 per band; rungs within ±5 of the 25 and 55 edges, with the 55
  edge double-covered.
- Each task defines all three oracle variants (thin/standard/strong) and names the
  independent check that makes `strong` non-gameable.
- The weak-model-fails screen is specified as the admission gate, with a recorded
  per-task outcome format, and its admission and rejection rules are exact
  complements (Part B).
- `scores.toml` blind-scored by two raters (as v1), not author-only.
- **Per-arm rendering** (already true): every arm lands on the tier ladder and its
  per-arm quality/cost means render, satisfied 2026-07-14 by the arm-resolution
  generalization. Verify by feeding a **synthetic fixture ledger** (crossed arm
  names, hand-set verifier results) through `calibration.py` — **not** by a dry-run,
  which produces no trials and so exercises none of the rendering.
- **Oracle-axis analysis** (a build task, NOT satisfied by the above): `calibration.py`
  gains an arm → (tier, oracle) resolver and a model×oracle interaction/slope
  estimator, so the three same-model oracle variants no longer collapse to one arm
  per tier (see Part C). This is the code the crossing needs; it is scoped here and
  built before the paid matrix, gated behind ADR-0008.
- **ADR-0008 accepted** — the oracle-quality factor and the 3×3 crossing are a new
  experimental dimension beyond ADR-0007's two knobs, recorded as their own decision
  before any build or spend.

## Cost & staging (deferred; needs approval)

- **Screen (cheap):** 2 arms × 9 tasks × 5 repeats ≈ **90 spawns**. This is the gate
  worth paying for first — it validates the bank before the matrix.
- **Full crossed matrix:** 3 models × 3 oracles × 9 tasks × 5 repeats ≈ **405
  spawns**. Needs explicit `--max-budget-usd` and separate approval per ADR-0007.
- Report tokens beside est-$ (playbook cost caveat: a newer, token-heavier model can
  cost more per task at a lower per-token price).

Neither is run here. This document is the plan; the spend is a human decision.

## Plug-in to the playbook

On build-out, `recalibration-playbook.md` gets two edits:

- **Step 1** offers `model-tier-v2` (+ `scenarios/model-tier/` arms crossed with the
  three oracles) as the calibration bank once it passes the screen; `model-tier-v1`
  stays as the resume-safe baseline.
- **Known limitation** section points here as the plan of record and, after a run,
  is rewritten to state the observed separation and the oracle-quality result.

## Provenance

Completes the `fathom-bank` stream of the choosing-models rollout (design
`craft-collection/docs/design/2026-07-14-choosing-models-skill.md`, Rollout 3). The
stream is authored, not run: the bank design and the screen are the deliverable;
the paid matrix is a separate, human-approved step.
