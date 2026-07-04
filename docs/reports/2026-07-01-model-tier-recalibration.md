# fathom report — the series engine model-tier recalibration on the current lineup

- **Date:** 2026-07-01
- **Bank:** `model-tier-v1` (dataset_version 1) — 7 stdlib-Python bugfix/feature tasks (scores 18–67)
  + sealed holdout (`fix-dedup-records`). n=5/cell, blind harness-side verifier grading.
- **Arms:** single-session, `effort=high`, differ ONLY by `model` — `haiku` (`claude-haiku-4-5`),
  `sonnet` (`claude-sonnet-4-6`, June), **`sonnet5` (`claude-sonnet-5`, NEW)**, `opus` (`claude-opus-4-8`).
  The Haiku / Sonnet-4.6 / Opus cells were **resume-reused** from the 2026-06-16 run (unchanged
  `config_hash`); only the Sonnet 5 arm ran fresh (35 trials). Tightest possible isolation of the one
  variable that changed (mid model).
- **Why:** re-measure calibration after the series engine bumped `mid` Sonnet 4.6 → Sonnet 5. Prior finding
  (2026-06-16): the score→tier map over-provisions; on-diagonal 1/7; the score does not predict
  model-difficulty (root-cause locality does).

## Findings

**1. Over-provisioning reproduces on the current lineup.** On-diagonal **1/7**. Per-task hard-criteria
quality fraction:

| task | score | predicted | Haiku | Sonnet4.6 | **Sonnet5** | Opus | empirical |
|---|---|---|---|---|---|---|---|
| fix-clamp | 18 | weak | 100% | 100% | 100% | 100% | weak ✓ |
| fix-titlecase | 26 | mid | 100% | 100% | 100% | 100% | weak (mid→weak) |
| fix-interval-merge | 39 | mid | 100% | 100% | 100% | 100% | weak |
| feature-csv-coalesce | 41 | mid | 100% | 100% | 100% | 100% | weak |
| fix-money-split | 44 | mid | 100% | 100% | 100% | 100% | weak |
| **fix-nonlocal-parse** | 65 | strong | 40% | 60% | **80%** | 100% | capacity ladder |
| fix-nonlocal-urlkey | 67 | strong | 100% | 100% | 100% | 100% | weak (strong→weak) |

6/7 tasks are aced by weak (Haiku); mid and strong buy **+0.00 quality** there (dose-response, weak/mid bands).

**2. One task discriminates — and Sonnet 5 climbs the ladder.** `fix-nonlocal-parse` (cross-module
root-cause) is the only task with a monotonic capacity effect. On its two hard criteria
(`codes_quoted_tagged`, `messages_quoted`): 40% → 60% → **80%** → 100% across Haiku / Sonnet 4.6 /
**Sonnet 5** / Opus. The Sonnet 4.6→5 upgrade closes most of the mid→strong gap, so **strong/Opus
trends toward escalation-only** (directional at n=5, not final).

**3. Score still does not predict model-difficulty.** `fix-nonlocal-urlkey` (67) is aced by all tiers
while `fix-nonlocal-parse` (65) is not — same score, opposite difficulty. The discriminant is root-cause
locality, not the prompt-complexity score. The `pr-prompt-scorer` cross-shape floor addresses the
sub-26 corner but does not separate within-strong.

**4. Cost caveat — mid is not automatically cheaper per task.** Economy (est USD is a token×price
estimate; real charge ≈ $0 under subscription auth):

| arm | mean quality | est $/trial | Pareto | note |
|---|---|---|---|---|
| haiku | 0.91 | $0.087 | ★ | |
| sonnet (4.6) | 0.94 | $0.142 | ★ | |
| opus | 1.00 | $0.247 | ★ | |
| **sonnet5** | 0.97 | **$0.336** | (dominated) | token-heavy: new tokenizer + adaptive-thinking-on |

Sonnet 5 landed **above Opus** on est $/trial despite a lower per-token price, because at `effort=high`
it runs adaptive thinking by default and the new tokenizer inflates counts ~30%. Treat as a caveat
(verify realized cost), not a robust cost ranking — n=5, cache-inclusive est, June/July measurement mix.

## Calibration decision

**No numeric threshold change.** Rationale: (a) same over-provisioning as June, on the same narrow
cross-module-bugfix distribution the `model-tiers` skill already flags as "recalibrate per distribution";
(b) the bank **over-saturates** (6/7 tasks aced by all tiers) so the whole signal rests on one task —
too thin at n=5 to move a boundary; (c) re-cutting global defaults on one distribution over-fits.
**Action taken:** model freshness (mid→Sonnet 5) shipped in the series engine; the `model-tiers` calibration note
extended with this run's evidence (Sonnet 5 narrows strong; the cost caveat).

## Limitations / next

- **The bank has low discriminating power** — highest-leverage fix is to add reliably tier-separating
  tasks (cross-module / displaced-cause / backend-parity at graded difficulty): the "boundary +
  heterogeneity" set. This also **unblocks the deferred efficiency study** (`pp-native-tier` vs
  `pp-all-sonnet5` vs `pp-fixed-opus`), which the 2026-06-19 pre-mortem showed cannot run without tier
  heterogeneity in the anchors.
- **Fable 5 (frontier)** not measured — opt-in, no scoring band; deferred.
- **Efficiency / engine-series arms** deferred pending separate budget approval.

**Cost this round:** ≈ **$11.4** estimated list-equivalent (Sonnet 5 arm, 35 trials), ≈ **$0 real**
(subscription auth); ceiling $75. Cached arms reused free. Scorecard: `report/scorecard-model-tier-v1.md`.
