# Is the series engine's complexity → model-tier mapping well-tuned? A fathom calibration study

- **Date:** 2026-06-16
- **Bank:** `model-tier-v1` (dataset_version 1) · **Arms:** Haiku 4.5 / Sonnet 4.6 / Opus 4.8 at `effort=high`
- **Instrument under test:** `series-engine:model-tiers` + `series-engine:pr-prompt-scorer`, pinned the series engine **0.8.1** @ `1c2748f3004c7c32e67b9379944b92e3777020a6`
- **Spec:** `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md` (keel-DoR certified; 4 pre-mortem rounds) · **ADR:** `docs/adr/0007-model-tier-calibration.md`
- **Status:** complete (verifier-fraction axis); pairwise judge deferred; effort sub-study reported in §5.5

## Executive summary

The series engine routes a coding task to a model by a complexity score: **0–25 → Haiku** (weak),
**26–55 → Sonnet** (mid), **56–100 → Opus** (strong). The skill ships with *no observed-run
calibration*. This study ran a difficulty-ladder of 7 stdlib-Python tasks on all three models,
scored blind on a per-task **hard-criteria quality fraction**, and joined cost.

**Verdict: on this task distribution the mapping over-provisions.** Only **1 of 7** tasks is
on-diagonal (predicted tier = empirically-cheapest-adequate tier). Five tasks the rubric routed
to mid/strong are **aced by Haiku** (over-provisioned); the per-band dose-response shows the weak
and mid bands buy **+0.00 quality** for **2–3× the cost**. The tier upgrade pays in exactly one
place — the cross-module root-cause task `fix-nonlocal-parse` (Haiku 40% → Sonnet 60% → Opus
100% on its hard criteria). Crucially, that task and its near-identically-scored sibling
`fix-nonlocal-urlkey` (rubric 65 vs 67) diverge completely empirically — one needs Opus, one is
aced by Haiku — so **the rubric's score does not predict where the stronger model is actually
needed** (prompt-complexity ≠ model-difficulty). And on that one discriminating task, raising the cheaper models' *thinking* (`effort=xhigh`) did **not** recover the gap to Opus — **capacity, not effort, is the lever** there. The whole study cost ~**$20** (vs an $80–120
ceiling).

**The headline caveat, stated up front:** these tasks turned out *easier for Haiku 4.5* than
their rubric scores implied. So the result is "for small, well-specified, mostly single-file
Python fixes/features, the mapping routes higher than necessary" — not a claim about all coding
work. The actionable core that *does* generalize: **the score is a prompt-complexity proxy that
does not isolate the cross-module/root-cause reasoning where the strong tier earns its cost.**

## §1 Background and question

`model-tiers` is the routing policy every series depends on. Its thresholds (25/55) and
tier assignments are reasoned, not measured — the skill itself notes "no observed-run
calibration." fathom is a scenario-blind tool-effectiveness harness: it runs the same task under
different configurations (here, different models), scores the final workspace blind, and joins
economy after scoring. Because `model` and `effort` are already hashed scenario fields, an arm is
a `(model, effort)` pair with no new spawn-path code.

**Research question.** Is the complexity→tier mapping *well-tuned* — i.e., for a task the rubric
routes to tier T, is T the cheapest model that delivers near-best quality? Equivalently: does the
empirically-right tier match the predicted tier across the difficulty range?

## §2 Hypotheses / predicted signal (pre-registered in the bank README)

- **low band (≤25)** ⇒ all three models pass (Haiku ceiling confirms the weak tier suffices).
- **mid band (26–55)** ⇒ Haiku mixed, Sonnet passes.
- **high band (56–100)** ⇒ Haiku fails the hard criteria (patches the symptom, leaves the second
  consumer broken); Opus passes by fixing the shared root cause.

A blind second rater confirmed the pre-mortem's **FM-3**: the rubric clusters single-file
bugfixes in the low-mid 30s–40s and jumps to ~61 for cross-module tasks, structurally avoiding
the 55 boundary (its own worked examples are 5/48/91). So the **25 boundary is probed**
(titlecase ≈ 26) but the **55 boundary is only bracketed** (money 44 ↔ nonlocal 65), not hit.

## §3 Design

**Factorial:** `model × task`, fully crossed, **5 repeats/cell**. Arms differ only by `model`
(`claude-haiku-4-5` / `claude-sonnet-4-6` / `claude-opus-4-8`) at `effort=high`; identical
allowlist, single-session strategy, limits (sized for the weakest model's longer runs, FM-12). No
plugins, no `Task` — a clean single-session solve so nothing confounds the model axis.

**Quality metric (the load-bearing axis).** Per task, each `verify.py` emits multiple escalating
boolean criteria, of which ≥2 are designated **hard** (capability-gated). The calibration scalar
is the **hard-criteria fraction** `(#true hard)/(#hard)` — computed over hard criteria only so a
single capability failure (0.5 on a 2-hard task) always exceeds ε rather than being diluted by
easy criteria. The full criteria set still feeds the per-criterion table and dose-response.

**"Right tier."** The cheapest model whose mean hard-fraction is within **ε = 0.10** of the best
AND whose Wilson CI (criteria pooled across trials: `successes = Σ true hard`, `n = Σ total hard`)
overlaps the best's. A tier whose ε-decision rests on overlapping CIs is labeled **indeterminate**,
never forced onto the diagonal. The mapping is *well-tuned* iff predicted tier = empirically-right
tier; off-diagonal-below = under-provisioned (quality lost), off-diagonal-above = over-provisioned
(cost wasted).

**Two knobs.** Model is capacity; `effort` is thinking. The mapping manages only the first. Effort
was staged: the main matrix fixed `effort=high`; a targeted effort sub-study (§5.5) probed the one
task with headroom.

**Bank.** 7 working tasks + 1 sealed holdout, one genre (Python fix/feature in small modules),
spread across the score range; 6 reused from prior banks (already graded with hard discriminating
criteria), 2 authored fresh at the low end. Each task scored by two independent raters; final =
average (`scores.toml`).

## §4 Methodology

- **Blindness (ADR-0003):** `verify.py` reads only the final workspace; no scenario/model identity
  in argv/env. Economy joined after scoring.
- **Statistics:** Wilson 95% CI on the pooled hard-criteria proportion. At 5 repeats/cell the CIs
  are wide — results are **directional**, and the report marks indeterminate tiers rather than
  over-claiming.
- **Cost:** subscription auth reports `total_cost_usd = 0` (D2), so the cost axis is the token×price
  **estimate** using the pinned `model-tiers` per-1k rates — not billed dollars.
- **Rails:** `fathom smoke` (8/8, real-spawn isolation) before any spend; `--dry-run` upfront; a
  cost-probe **pilot** (`--repeats 2`, 42 trials) gated the full spend on a quantitative
  discrimination predicate; per-spawn `--max-budget-usd` cap; idempotent resume (the pilot's trials
  counted toward the full matrix — zero waste).
- **Pilot GO predicate (§9 of the spec):** proceed only if ≥1 high-band hard criterion shows Haiku
  ≤60% AND Opus ≥80% at n≥5. **Met:** `fix-nonlocal-parse` (Haiku 40%, Opus 100%).

## §5 Results

105 trials (35/arm), all completed, no infrastructure errors.

### 5.1 Per-criterion (hard criteria; n=5/arm)

Every criterion on every task is **100% across all three models EXCEPT** the two hard criteria of
`fix-nonlocal-parse`:

| Criterion (task) | Haiku | Sonnet | Opus |
|---|---|---|---|
| `messages_quoted` (nonlocal-parse) | **40%** (2/5) | **60%** (3/5) | **100%** (5/5) |
| `codes_quoted_tagged` (nonlocal-parse) | **40%** (2/5) | **60%** (3/5) | **100%** (5/5) |
| all other hard criteria (6 tasks) | 100% | 100% | 100% |
| `regression_test_present` (all) | 0% | 0% | 0% |

`regression_test_present` is 0% everywhere — the tasks do not ask for a test and nothing prompts
one, so it carries no model signal (it is not a hard criterion and does not enter the calibration).

### 5.2 Calibration confusion matrix (predicted vs empirically-right tier)

| predicted ↓ / empirical → | weak | mid | strong | indeterminate |
|---|---|---|---|---|
| **weak** | 1 | 0 | 0 | 0 |
| **mid** | 4 | 0 | 0 | 0 |
| **strong** | 1 | 0 | 0 | 1 |

**On-diagonal (well-tuned): 1/7.** Per task: clamp (18, weak→weak ✓); titlecase (26),
interval-merge (39), csv-coalesce (41), money-split (44) — all **mid→weak** (over-provisioned);
nonlocal-urlkey (67) **strong→weak** (over-provisioned); nonlocal-parse (65) **strong→indeterminate**
(Haiku 40% / Sonnet 60% / Opus 100% — Opus is best, but Sonnet's CI overlaps Opus's, so "Opus
required" vs "Sonnet adequate" can't be resolved at n=5).

### 5.3 Dose-response (mean hard-fraction quality × mean cost, by band)

| band | Haiku | Sonnet | Opus | Δq Haiku→Sonnet | Δq Sonnet→Opus |
|---|---|---|---|---|---|
| weak | 1.00 ($0.065) | 1.00 ($0.114) | 1.00 ($0.185) | +0.00 | +0.00 |
| mid | 1.00 ($0.096) | 1.00 ($0.146) | 1.00 ($0.247) | +0.00 | +0.00 |
| strong | 0.70 ($0.080) | 0.80 ($0.150) | 1.00 ($0.279) | +0.10 | +0.20 |

The weak and mid bands buy **zero** quality per upgrade at 1.8–2.6× the cost. Only the strong band
(driven entirely by nonlocal-parse; urlkey is 100% everywhere) rewards the upgrade.

### 5.4 Cost-quality Pareto frontier (corrected, strict non-domination)

| arm | mean quality | mean $/trial | frontier |
|---|---|---|---|
| Haiku | 0.91 | $0.087 | ★ |
| Sonnet | 0.94 | $0.142 | ★ |
| Opus | 1.00 | $0.247 | ★ |

All three are non-dominated, but the spacing tells the story: Haiku delivers 91% of perfect quality
at 35% of Opus's cost; Sonnet adds 3 points for +63% cost (it only ever edges Haiku via partial
credit on nonlocal-parse, 60% vs 40%, and never reaches Opus's reliability); Opus buys the last 6
points — but those 6 points live almost entirely in one task. (The harness's *old* efficiency view
flagged Sonnet/Opus as "Pareto" via a "beats some arm" test; this study added a correct strict
non-domination frontier — see ADR-0007 / §8 of the spec.)

### 5.5 Effort sub-study — can thinking substitute for capacity?

The full matrix showed headroom for effort to matter on exactly one task (`fix-nonlocal-parse`).
We re-ran the two cheaper models at `effort=xhigh` on that task (n=5) and compared against the
main matrix's `effort=high` baselines (Haiku 40% / Sonnet 60% / Opus-high 100%).

| arm (on `fix-nonlocal-parse`, n=5) | `messages_quoted` | `codes_quoted_tagged` | mean $/trial |
|---|---|---|---|
| Haiku @ `high` (baseline) | 40% | 40% | ~$0.08 |
| **Haiku @ `xhigh`** | **0%** (0/5) | **0%** (0/5) | $0.066 |
| Sonnet @ `high` (baseline) | 60% | 60% | ~$0.15 |
| **Sonnet @ `xhigh`** | **40%** (2/5) | **40%** (2/5) | $0.128 |
| Opus @ `high` (baseline) | 100% | 100% | ~$0.28 |

**Effort does not substitute for capacity here.** Cranking thinking from `high` to `xhigh` on the
two cheaper models did **not** close the gap to Opus — neither approached Opus's 100% (Haiku-xhigh
0%, Sonnet-xhigh 40%). Both even scored at or below their `high` baselines, though the apparent dip
is within n=5 noise; the robust signal is **no lift**. The capability the cross-module root-cause
fix needs is **model capacity, not thinking budget** — more reasoning tokens on a weaker model did
not buy the missing capability. (`xhigh` was accepted on live spawns with no infrastructure error —
the FM-7 acceptance concern is cleared.)

## §6 Analysis

1. **The mapping over-provisions for this distribution.** 6 of 7 tasks are routed to a tier more
   capable (and 1.8–2.9× more expensive) than the empirically-cheapest-adequate one. The weak and
   mid bands deliver identical quality (100%) across all three models.
2. **The strong tier earns its cost in one specific shape:** the cross-module, root-cause bug
   (`nonlocal-parse`), where a weak model patches the symptom site and leaves the second consumer
   broken, and only the stronger model fixes the shared helper. This is exactly the "deep reasoning
   / non-local" character the strong tier is meant for — and it is the *only* place the tier system
   paid off here.
3. **The rubric score does not predict model-difficulty.** `nonlocal-parse` (65) and
   `nonlocal-urlkey` (67) score within 2 points and are the same structural genre (cross-module
   root cause), yet Haiku aces urlkey (URL canonicalization) and fails parse (quoted-field parsing
   with a shared root cause). Prompt-complexity ≈ identical; model-difficulty ≈ opposite. The
   routing signal the rubric lacks is *how hard the reasoning actually is for a weak model*, which
   prompt features only weakly proxy.
4. **Sonnet (the mid tier) is the weakest value proposition here:** it costs 63% more than Haiku
   and its only quality gain is partial credit on the one hard task (60% vs 40%) — it never reaches
   Opus's reliability. On this distribution there is little for the mid tier to do that Haiku can't
   (cheaper) or that needs Opus.

## §7 Threats to validity

- **Bank easiness (dominant caveat).** Modern Haiku 4.5 is genuinely capable on small, well-specified,
  mostly single-file Python tasks. The over-provisioning finding is partly "this bank is easy for
  Haiku." It generalizes to *that task class*, not to large-context, multi-file, or
  domain-heavy work. A harder bank (where Haiku fails the mid band too) would relocate the
  crossover; this study cannot.
- **Small n.** 5 repeats/cell → wide Wilson CIs; the verdict is directional. `nonlocal-parse` is
  genuinely indeterminate (mid vs strong) at this n.
- **Boundary-placement is coarse.** The rubric clusters scores away from 55 (confirmed by the blind
  rater), so the 55 cut is bracketed (44 ↔ 65), not pinpointed; the weak band is thin (1 solid +
  1 boundary task). The study tests *tier-level* calibration well and *boundary placement* only
  approximately.
- **Pooled-CI independence.** The pooled hard-criteria proportion treats correlated criteria as
  independent; the CI is a heuristic width, not exact coverage.
- **Cost is an estimate** (subscription billing reports $0; token×price proxy).
- **Quality axis is verifier-only.** The pairwise judge (qualitative design/readability) was built
  into the spec but deferred; this verdict rests on mechanical hard-criteria correctness, which may
  miss quality differences the criteria don't capture.
- **One operator's distribution, Windows host, one run.**

## §8 Conclusion and recommendation to `model-tiers`

**On this task distribution, the complexity→tier mapping is not well-tuned: it over-provisions.**
A weak model (Haiku) is the cheapest adequate choice for 6 of 7 tasks; the strong tier pays off
only on genuine cross-module root-cause reasoning, which the rubric score does not isolate.

Recommendations, ordered by confidence:

1. **(High confidence) The score is a coarse proxy; validate per task-distribution.** The same
   rubric score (65 vs 67) produced opposite model-difficulty. Teams should not treat the
   score→tier map as calibrated for their work without an observed-run check like this one. This
   directly fills the "no observed-run calibration" gap the skill admits.
2. **(Med) Add a root-cause/locality signal to the scorer.** The one discriminating feature here
   was *cross-module shared-root-cause* reasoning. A rubric dimension that detects "the fix is not
   where the symptom is" / "multiple consumers of a shared helper" would isolate the strong-tier
   cases far better than the current prompt-complexity proxies.
3. **(Med, distribution-specific) For simple-bugfix-heavy distributions, route lower.** For small,
   well-specified, single-file Python fixes/features, Haiku is sufficient and Sonnet adds cost
   without reliability; reserving Sonnet/Opus for detected cross-module/root-cause work would cut
   cost materially at no quality loss *on this class*. This is **not** a recommendation to globally
   lower the thresholds — it is contingent on the task class, given the bank-easiness caveat.
4. **(Med, narrow) Effort is not a substitute for the upgrade on root-cause work.** On the one task
   where the tier upgrade paid, raising the cheaper models to `xhigh` thinking did not recover
   Opus's capability (§5.5). So `model-tiers` should **not** offer an "add effort instead of
   upgrading" shortcut for cross-module/root-cause tasks — capacity is the lever there. (Effort may
   still help other task shapes this bank does not represent; tested on n=5, one task.)

## §9 Future work

- A **harder bank** where Haiku fails the mid band, to locate the crossover precisely (this bank
  ceilings below the strong tier).
- **Light the pairwise judge** (built, deferred) to add the qualitative axis the verifier misses.
- **A locality/root-cause scorer feature** and a re-run to test recommendation #2.
- Run the **sealed holdout** (`fix-dedup-records`) as a generalization check.
- More repeats on `nonlocal-parse` to resolve its mid-vs-strong indeterminacy.

## Appendix A — Reproducibility

```sh
uv run fathom smoke                                                   # 8/8 real-spawn isolation
uv run fathom run model-tier-v1 --scenarios-dir scenarios/model-tier --dry-run --repeats 5
uv run fathom run model-tier-v1 --scenarios-dir scenarios/model-tier --repeats 5 --max-budget-usd 3.0
uv run fathom report model-tier-v1
```

- Ledger: `ledger/model-tier-v1.jsonl` (105 trials) + `ledger/model-tier-effort.jsonl`.
- Scorecard: `report/scorecard-model-tier-v1.md` (regenerable).
- Economy (full matrix, est. USD): Haiku $2.95 / Sonnet $4.84 / Opus $8.40 → **$16.2** for 105
  trials; whole study incl. smoke + pilot + effort ≈ **$20** (vs $80–120 ceiling). Per-trial: Haiku
  ~$0.084, Sonnet ~$0.138, Opus ~$0.240 (Opus ≈ 2.9× Haiku). Note Haiku used **more turns** (427 vs
  Opus 282) — the weaker model iterates more — validating the weakest-model limit sizing (FM-12).

## Appendix B — Per-task detail

| task | score (auth/rater) | predicted | empirical | Haiku | Sonnet | Opus |
|---|---|---|---|---|---|---|
| fix-clamp | 10 / 25 → 18 | weak | weak ✓ | 100% | 100% | 100% |
| fix-titlecase | 22 / 30 → 26 | mid | weak | 100% | 100% | 100% |
| fix-interval-merge | 45 / 33 → 39 | mid | weak | 100% | 100% | 100% |
| feature-csv-coalesce | 40 / 43 → 41 | mid | weak | 100% | 100% | 100% |
| fix-money-split | 55 / 33 → 44 | mid | weak | 100% | 100% | 100% |
| fix-nonlocal-parse | 70 / 61 → 65 | strong | indeterminate | 40% | 60% | 100% |
| fix-nonlocal-urlkey | 74 / 61 → 67 | strong | weak | 100% | 100% | 100% |
| *fix-dedup-records (holdout)* | 50 / 30 → 40 | mid | *(sealed)* | — | — | — |
