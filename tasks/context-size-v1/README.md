# context-size-v1 — interdependence-at-volume matched-pair bank

Tests whether **large context flips the model-tier over-provisioning verdict**. Each matched pair
embeds the **same planted bug** in a SMALL workspace (≤5 files) vs a LARGE one (the same
2–3 contract modules buried among ~40 import-coherent siblings). The bug, the contract
modules, the verifier, and the symptom-only instruction are **byte-identical** across a
pair (`tests/test_context_bank.py::TestPairIdentity`); only the navigable volume differs.

The question: **does interdependence at *volume* push the empirically-right tier higher
than the same cross-module fix did at small volume?** ("Volume" is entangled with locality
by design — ADR-0008 D2; the verdict is framed as "does volume add a tier requirement
*beyond* locality.")

## Pairs (difficulty score → predicted tier)

| pair | pkg | bug (root) | contracts the fix needs | score | predicted | kind |
|---|---|---|---|---|---|---|
| `shipping-tax` | shopcart | total uses stale threshold + tax | `config`, `rates` | 34 | mid | interdependence |
| `loyalty-reward` | rewards | flat rate ignores customer tier | `accounts` → `loyalty` (2-hop) | 48 | mid | interdependence |
| `nonlocal-sku` | warehouse | shared `keys.sku_key` ignores aliases | `aliases` (+ 2 callers) | 64 | strong | interdependence (nonlocal root) |
| `slug-control` | textkit | one-file slugify (collapse + strip) | — (no contract) | 18 | weak | **negative control** |

Each pair has `<pair>-small` and `<pair>-large` (identical bug; large adds 40 distractors).
The negative control's distractors are **ignorable** (import nothing under test) — it tests
whether *ignorable* volume bites at all (it should not; the FM-1 null lower-bound).

## Predicted signal (per pair)

- **SMALL ⇒ weak model passes.** Each bug is seeded from the empirically weak-passable shape
  (ADR-0008 D4 / FM-A: the `urlkey` family Haiku aced at 100%, not the `parse` family it
  floored at 40%), so the weak model handles the cross-module fix when the modules are right
  there.
- **LARGE ⇒ if volume bites, the weak model's hard-criteria fraction drops below the strong
  model's by >ε (0.10)** — it can't locate/track the 2–3 needles among 40 siblings.
- **Negative control ⇒ no small→large drop** (ignorable volume is Grep-skippable).

If the interdependence pairs show the drop and the control does not, **context-scope is a
real routing feature**; if the weak model aces both sizes, synthetic volume does not bite.

## Pilot gate (§8) — run BEFORE the full spend

`fathom run` is task-major, so `--limit` runs whole tasks first (15 trials/task at
`--repeats 5`: 3 arms × 5). The pilot is the first slice of the (resumable) full bank — its
trials count toward the full matrix, no re-spawn.

```sh
uv run fathom smoke                                                    # go/no-go gate (spends a little)
uv run fathom run context-size-v1 --scenarios-dir scenarios/context-size --dry-run
# Pilot: the two interdependence pairs nearest the boundary at n=5 (loyalty-reward +
# nonlocal-sku = first 4 tasks alphabetically = 60 trials), plus the control:
uv run fathom run context-size-v1 --scenarios-dir scenarios/context-size --repeats 5 \
    --limit 60 --max-budget-usd 3
# evaluate (see below); then add the control + remaining pair, then finish (resume):
uv run fathom run context-size-v1 --scenarios-dir scenarios/context-size --repeats 5 \
    --max-budget-usd 3
uv run fathom report context-size-v1
```

**GO predicate (two-sided, floor-guarded, negative-control-gated, n≥5)** — all on the
pooled **hard-criteria fraction** (the ADR-0007/§7 scalar, NOT all-truthy pass/fail):

1. **weak-SMALL ≥ 80%** — the fix is within weak reach at low volume (else the pair can't isolate volume).
2. **weak-LARGE ≤ 60%** — volume pushes it out of weak reach.
3. **strong-LARGE ≥ 80%** — the strong model recovers it at volume (else the large task is just unsolvable).
4. **negative control: no weak small-vs-large drop > ε** — the drop is interdependence-at-volume, not a broken fixture.

Record **which strong tier (mid or strong) first recovers LARGE** — if Sonnet also ≥80%
the shift is weak→mid, not weak→strong (FM-N6). Confirm **no LARGE trial truncated to
ERRORED** (a false ceiling from undersized navigation budget; FM-7) — `fathom report` and the
ledger show ERRORED trials.

Baseline from study 1: the nearest SMALL cross-module task gave Haiku 40% / Sonnet 60% /
Opus 100% and was *indeterminate* at n=5, so a clean ≥80/≤60 separation is the required
signal and its absence is a true NO-GO. **Record the GO/ADJUST decision here before the full
spend, and the phase-2 decision.**

## Pilot outcome (2026-06-16) — NO-GO

60 trials (haiku × all 8 tasks n=5 = 40; opus × the 2 interdependence pairs n=5 = 20), **0
errors / 0 ERRORED-truncations** (FM-7 clear), **~$10.2** (haiku $3.32 / opus $6.87). All on
the hard-criteria fraction (the GO scalar):

| pair (score) | haiku small | haiku large | opus large | small→large right-tier |
|---|---|---|---|---|
| shipping-tax (34) | 100% | 100% | — | weak = weak |
| loyalty-reward (48) | 100% | 100% | 100% | weak = weak |
| nonlocal-sku (64) | 100% | 100% | 100% | weak = weak |
| slug-control (18, control) | 100% | 100% | — | weak = weak |

**GO predicate:** clause 1 (weak-SMALL ≥80%) ✓ on all; **clause 2 (weak-LARGE ≤60%) FAILS on
all — weak-LARGE = 100%** → **NO-GO**. Haiku locates and correctly fixes the cross-module bug
among ~40 coherent distractors under behavior-only instructions (no package name) and
grep-resistant fixtures (~328k mean cache-tokens — it ingests the volume), just as in the
≤5-file workspace. The negative control behaves identically (as predicted: ignorable volume
is skippable). Empirical right-tier = **weak** for all 8 tasks → the model-tier
over-provisioning **persists at volume**.

**Decision:** do NOT run the rest of the synthetic matrix (the sonnet arm + n=5 fill) — the
signal is unambiguous across all 4 pairs and the gate exists precisely to avoid that spend.

**Threat to validity → phase-2 decision:** synthetic distractors are coherent but *shallow*;
they may not capture what makes REAL large-codebase work hard (deep hops, subtle real
contracts, domain ambiguity). This NO-GO is "synthetic volume of *this kind* does not bite,"
NOT "context never matters." A real-codebase external-validity follow-up (deeper hops,
subtle real contracts, domain ambiguity) is the higher-value next step *because* synthetic
didn't bite.

## Cost

48 trials at `--repeats 2` → $96 ceiling ($2/trial, conservative). Full matrix `--repeats 5`
= 120 trials; large-context trials are pricier than model-tier's (~$0.3–1.5/trial for the
40-module navigation, ~$0.15–0.3 for small) → estimate **~$50–80** for the full phase-1
matrix. Rails: `PYTHONIOENCODING=utf-8`, `--limit` batches, `--max-budget-usd 3` per spawn,
`fathom smoke` at every resume.

## Notes

- Difficulty scores are **author** pr-prompt-scorer estimates (single rater). They are
  scaffolding for the predicted-tier column; the headline is the empirical small→large
  shift. Load-bearing: SMALL and LARGE share a score because they ship the *identical*
  prompt (`scores.toml`) — exactly the gap the study probes.
- `gen_distractors.py` (re)materialises every large fixture deterministically from the
  committed small core. `bugfix_verify.py` is the shared, scenario-blind verifier helper.
