# Does context volume shift the model tier? — the context-size matched-pair study

- **Date:** 2026-06-16 (pilot matrix + NO-GO decision, recorded at the time in the bank README;
  promoted to this findings report 2026-07-09)
- **Bank:** `context-size-v1` (dataset_version 1) — 4 matched small/large task pairs ·
  **Ledger:** `ledger/context-size-v1.jsonl` (60 trials, 0 errors) · **Scorecard:**
  `report/scorecard-context-size-v1.md` (regenerate: `uv run fathom report context-size-v1`)
- **Arms:** `haiku` (claude-haiku-4-5) and `opus` (claude-opus-4-8), single-session,
  `effort=high`, identical but for `model` (`scenarios/context-size/`). A `sonnet` arm was
  authored and **deliberately never run** (see the NO-GO).
- **Design docs:** the bank README (`tasks/context-size-v1/README.md`) carries the full design,
  GO predicate, and the recorded pilot outcome; it cites ADR-0008 (D2, D4), which was lost in
  the 2026-07 history squash — the decisions survive only as citations there.

## Question

The model-tier studies (2026-06-16, recalibrated 2026-07-01) found the complexity→tier mapping
**over-provisions**: Haiku aces most tasks the rubric routes to mid/strong. Those tasks were
small workspaces (≤5 files). This study asks whether **interdependence at volume** is what the
rubric's higher tiers are actually paying for: the same planted cross-module bug, the same
contract modules, the same symptom-only instruction — byte-identical across each pair
(`tests/test_context_bank.py::TestPairIdentity`) — but the large member buries the 2–3 relevant
modules among **~40 import-coherent distractor siblings**. If volume bites, the weak model's
hard-criteria fraction should drop >ε (0.10) small→large while the strong model recovers it;
a `slug-control` negative-control pair (ignorable distractors) guards against "any volume
breaks the fixture".

| pair | bug (root) | score → predicted tier | kind |
|---|---|---|---|
| `shipping-tax` | total uses stale threshold + tax (`config`, `rates`) | 34 → mid | interdependence |
| `loyalty-reward` | flat rate ignores customer tier (2-hop contract) | 48 → mid | interdependence |
| `nonlocal-sku` | shared key fn ignores aliases (nonlocal root, +2 callers) | 64 → strong | interdependence |
| `slug-control` | one-file slugify | 18 → weak | negative control |

Scores are single-rater scaffolding; small and large members share a score *by construction*
(the scorer reads the prompt, which is identical) — that blindness to volume is exactly the gap
probed.

## Result — synthetic volume does not bite (NO-GO at the pilot gate)

Pilot: haiku × all 8 tasks (n=5, 40 trials) + opus × the two harder pairs (n=5, 20 trials);
0 ERRORED-truncations (the FM-7 false-ceiling check was clear). On the pooled hard-criteria
fraction (the GO scalar):

| pair (score) | haiku small | haiku large | opus large | small→large right-tier shift |
|---|---|---|---|---|
| shipping-tax (34) | 100% | 100% | — | weak = weak |
| loyalty-reward (48) | 100% | 100% | 100% | weak = weak |
| nonlocal-sku (64) | 100% | 100% | 100% | weak = weak |
| slug-control (18, control) | 100% | 100% | — | weak = weak |

GO clause 1 (weak-SMALL ≥ 80%) passed everywhere; **clause 2 (weak-LARGE ≤ 60%) failed
everywhere — weak-LARGE = 100%** → **NO-GO**, recorded 2026-06-16. Haiku locates and correctly
fixes the cross-module bug among ~40 coherent distractors under behavior-only instructions
(~328k mean cache-read tokens per trial — it ingests the volume) exactly as it does in the
≤5-file workspace. The negative control behaved identically, as predicted.

**Calibration read:** empirically-right tier = weak for all 8 tasks; predicted-vs-empirical
on-diagonal **2/8** (only the negative control's two members). The model-tier
**over-provisioning persists at volume** — interdependence-at-volume, in this synthetic form,
is *not* the missing feature that justifies the higher tiers.

## Economy

| arm | mean quality (hard-criteria) | mean est $/trial | note |
|---|---|---|---|
| haiku | 1.00 | $0.085 | Pareto frontier |
| opus | 1.00 | $0.361 | +0.00 quality for ~4.2× cost |

Pilot spend ~$10.2 (haiku $3.32 / opus $6.87), token×price estimate under subscription auth.

## The retired sonnet arm

The GO gate's recorded decision — "do NOT run the rest of the synthetic matrix (the sonnet arm
+ n=5 fill); the signal is unambiguous across all 4 pairs and the gate exists precisely to
avoid that spend" — is hereby made formal (2026-07-09). The remaining 60 cells (sonnet ×8×5,
opus fill ×4×5) print a $120 ceiling on `--dry-run` and are **verdict-inert**: the empirical
tier rule picks the cheapest model within ε of the best, and the cheapest tier is already at
100% on every task, so no sonnet result could move any cell. `scenarios/context-size/sonnet.toml`
(and the `scenarios/context-size-sonnet/` staging dir) are kept for reproducibility; the
resume key means a future deliberate run would simply append.

## Caveats / validity

1. **Synthetic distractors are coherent but shallow.** This NO-GO says "synthetic volume of
   *this kind* does not bite," not "context never matters." Real large-codebase work differs
   (deep hops, subtle real contracts, domain ambiguity) — a real-codebase follow-up is the
   higher-value phase-2 *because* synthetic didn't bite (recorded in the bank README's
   threat-to-validity note).
2. **The scorecard's headline pass-rate reads 0% for both arms** — an artifact:
   `regression_test_present` (a non-hard criterion) fails in all 60 trials while every other
   criterion is 100%, and the headline is an all-criteria AND. Bare single-session arms never
   write an unprompted regression test — consistent with `bare` = 0/10 in the humble-vs-super
   studies. The signal lives in the hard-criteria fraction (calibration section). Extends the
   standing "promote the hard-criteria fraction to the core report" item (STATUS open items).
3. **Ledger records carry no timestamps** (known gap), so the run date is fixed by the bank
   README's dated pilot-outcome entry, not by the ledger.
4. n=5 per cell; all-100% cells make CI overlap moot here, but the usual pooled-CI clustering
   caveat applies (ADR-0007 D3).

## Verdict line

**On matched pairs where only navigable volume differs, synthetic interdependence-at-volume
adds no tier requirement: the weak tier stays empirically right at 100% across all four pairs
(n=5), and the tier rubric's mid/strong routings remain over-provisioned. ~$10.2; the GO gate
saved the remaining ~$120 ceiling.** Directional, not final.
