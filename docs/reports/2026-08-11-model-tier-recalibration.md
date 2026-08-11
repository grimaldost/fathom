# fathom report — model-tier recalibration on the Opus 5 lineup

- **Date:** 2026-08-11
- **Bank:** `model-tier-v1` (dataset_version 1) — 7 stdlib-Python bugfix/feature tasks (scores 18–67)
  + sealed holdout (`fix-dedup-records`, excluded). n=5/cell, blind harness-side verifier grading.
- **Arms:** single-session, `effort=high`, differ ONLY by `model` — `haiku` (`claude-haiku-4-5`),
  `sonnet` (`claude-sonnet-4-6`), `sonnet5` (`claude-sonnet-5`), `opus` (`claude-opus-4-8`),
  **`opus5` (`claude-opus-5`, NEW)**. The four prior arms were **resume-reused** (unchanged
  `config_hash`); only the Opus 5 arm ran fresh (35 trials).
- **Why:** re-measure calibration after the strong-tier lineup move Opus 4.8 → Opus 5
  (`choosing-models` 0.9.0, CRAF-B06/T38b). Step 0 (lineup + mirrors) was completed elsewhere on
  2026-08-11 and is not re-done here.
- **Gates:** `fathom smoke` ALL PASS (8/8) before spending. Dry-run planned **35 trials
  (140 already done)** — only the new arm, confirming no shared field moved the cached arms'
  `config_hash`. Ceiling $70.00 under a `--max-budget-usd 75` rail.

**Instrument check (FATH-B49).** The scorecard pools economy by arm *name* across `config_hash`es.
Aggregating the ledger independently by `config_hash` returns five hashes for five names, one each —
nothing pooled, so the scorecard's per-arm economy is read as-is.

| arm | config_hash | trials | in-tok | out-tok | cache read | cache create | $ (list-equiv) |
|---|---|---|---|---|---|---|---|
| haiku | `37d8abcb` | 35 | 1,384 | 106,703 | 11,770,161 | 681,355 | 3.0987 |
| sonnet (4.6) | `030e5213` | 35 | 260 | 57,337 | 6,413,356 | 396,571 | 5.1884 |
| sonnet5 | `967c4949` | 35 | 128,947 | 56,101 | 9,521,536 | 502,658 | 11.8588 |
| opus (4.8) | `345d6963` | 35 | 104,955 | 74,971 | 6,206,618 | 325,485 | 8.7813 |
| **opus5** | `ab1570c2` | 35 | 460 | 110,933 | 8,168,546 | 542,962 | **12.3141** |

The `$` column is the CLI's own reported cost where it is non-zero (fathom falls back to a
token×price estimate only when the CLI reports 0). Treat it as **list-equivalent**; the real charge
under subscription auth is ≈ $0.

## Findings

**1. On-diagonal rate is unchanged: 1/7.** Third consecutive measurement at the same value
(2026-06-16, 2026-07-01, and now). The confusion matrix:

| predicted ↓ / empirical → | weak | mid | strong | indeterminate |
|---|---|---|---|---|
| **weak** | 1 | 0 | 0 | 0 |
| **mid** | 4 | 0 | 0 | 0 |
| **strong** | 1 | 0 | 0 | 1 |

The reading that matters is the *column* margin, not the diagonal: of seven tasks, **six resolve to
`weak` and one is indeterminate. Not one task resolves to `mid` or `strong`.** The empirical outcome
is very nearly a constant on this bank.

**2. Per-task quality ladder — Opus 5 buys nothing over Opus 4.8, and the discriminating task
remains the only one with headroom.** Hard-criteria quality fraction:

| task | score | predicted | empirical | haiku | sonnet | sonnet5 | opus | **opus5** | note |
|---|---|---|---|---|---|---|---|---|---|
| fix-clamp | 18 | weak | weak | 100% | 100% | 100% | 100% | 100% | on-diagonal |
| fix-titlecase | 26 | mid | weak | 100% | 100% | 100% | 100% | 100% | mid→weak |
| fix-interval-merge | 39 | mid | weak | 100% | 100% | 100% | 100% | 100% | mid→weak |
| feature-csv-coalesce | 41 | mid | weak | 100% | 100% | 100% | 100% | 100% | mid→weak |
| fix-money-split | 44 | mid | weak | 100% | 100% | 100% | 100% | 100% | mid→weak |
| **fix-nonlocal-parse** | 65 | strong | indeterminate | 40% | 60% | 80% | 100% | **100%** | capacity ladder |
| fix-nonlocal-urlkey | 67 | strong | weak | 100% | 100% | 100% | 100% | 100% | strong→weak |

`fix-nonlocal-parse` stays the sole load-bearing task: 40 → 60 → 80 → 100 → 100 across
Haiku / Sonnet 4.6 / Sonnet 5 / Opus 4.8 / **Opus 5** on both hard criteria
(`messages_quoted`, `codes_quoted_tagged`). Opus 5 matches the Opus 4.8 ceiling and does not exceed
it, because there is no room above 100%. The other six tasks are aced by every arm, as before.

**3. Dose-response — the strong band's last rung is flat.** Per-band mean quality and $/trial:

| band | haiku | sonnet | sonnet5 | opus | opus5 |
|---|---|---|---|---|---|
| weak (1 task) | 1.00 / $0.065 | 1.00 / $0.114 | 1.00 / $0.286 | 1.00 / $0.185 | 1.00 / $0.283 |
| mid (4 tasks) | 1.00 / $0.099 | 1.00 / $0.156 | 1.00 / $0.333 | 1.00 / $0.253 | 1.00 / $0.338 |
| strong (2 tasks) | 0.70 / $0.080 | 0.80 / $0.150 | 0.90 / $0.377 | 1.00 / $0.279 | 1.00 / $0.414 |

Δquality for the Opus 4.8 → Opus 5 step is **+0.00 in every band**, at **+$0.135/trial** in the
strong band. Within-tier, the newer model is a pure cost increase on this distribution. The
weak→mid→strong rungs each buy +0.10 in the strong band and +0.00 everywhere else — the
over-provisioning finding, reproduced a third time.

**4. Cost-quality Pareto, tokens beside dollars.** Opus 5 is **dominated**: identical mean quality to
Opus 4.8 at 1.40× the cost.

| arm | mean quality | mean $/trial | in+out tokens | mean turns | mean wall (s) | frontier |
|---|---|---|---|---|---|---|
| haiku | 0.91 | $0.089 | 108,087 | 12.8 | 40.6 | ★ |
| sonnet (4.6) | 0.94 | $0.148 | 57,597 | 8.0 | 40.8 | ★ |
| opus (4.8) | 1.00 | $0.251 | 179,926 | 8.4 | 44.1 | ★ |
| sonnet5 | 0.97 | $0.339 | 185,048 | 9.1 | 33.1 | dominated |
| **opus5** | 1.00 | **$0.352** | 111,393 | 10.2 | 51.1 | dominated |

The playbook's cost caveat holds in a new shape here. Opus 5 is **token-lighter than Opus 4.8 on
in+out** (111k vs 180k) and still **costs 40% more per trial**, because the fresh-input volume moved
into cache (8.17M read + 543k created, vs 6.21M + 325k) and output grew 48%. Per-token price is
identical within the family, so the whole delta is volume — and the raw in+out column, read alone,
points the wrong way. Report the cache buckets or the ranking inverts.

**5. The one real Opus 5 difference sits outside the hard criteria.** `regression_test_present`:

| criterion | haiku | sonnet | sonnet5 | opus | **opus5** |
|---|---|---|---|---|---|
| regression_test_present | 0.0% (0/30) | 0.0% (0/30) | 3.3% (1/30) | 0.0% (0/30) | **70.0% (21/30)** |

This single criterion accounts for the entire headline pass-rate gap (opus5 26/35 = 74.3%; every
other arm 5–6/35 = 14–17%): the 5 passing trials on every other arm are the one task that does not
carry the criterion, and Opus 5 adds 21 more. Opus 5 writes a regression test for the bug it fixed in
70% of trials where four other models essentially never do. That is a **verification-behavior**
difference, not a capacity difference — it moves no hard criterion — and it is the most likely
proximate cause of the extra output tokens, the extra turns (10.2 vs 8.4) and the extra wall-clock.

It also bears on a live open question elsewhere: the `choosing-models` oracle-coverage discount
reasons about the oracle as a pre-existing fact of the environment, and here the executing model
authored a fresh oracle mid-run in most trials. The oracle a task will have is partly a function of
which model runs it. Recorded as an observation; this bank was not designed to test it, and the
crossed model × oracle-quality design that would (`docs/specs/2026-07-14-tier-separating-bank-design.md`)
remains unrun.

## Calibration decision

**No numeric threshold change. Calibration note (provenance) only** — the playbook's Step 3 rule,
applied as written: thresholds move only on a robust cross-distribution shift; a single narrow
distribution at small n updates the model-policy owner's calibration note instead.

Every precondition for "note, not thresholds" is met, and one of them is stronger than last time:

- **Same narrow distribution.** One corpus of seven cross-module Python bugfix/feature tasks. Nothing
  cross-distribution was measured, so nothing licenses a global re-cut.
- **The bank has no power to move a boundary.** Six of seven tasks are at 100% for all five arms.
  With 2 hard criteria × 5 repeats = 10 pooled Bernoulli observations per (arm, task), a 10/10 cell
  carries a Wilson 95% CI of **[0.72, 1.00]** — any true shortfall below ~28 points is invisible
  (~20 points for the 15-observation task). The bank cannot see a difference it was not built to
  hold.
- **The outcome variable is a near-constant.** No task resolves empirically to `mid` or `strong`. A
  threshold cut is a claim about where the outcome changes; on this bank the outcome does not change.
- **This run added an arm, not discriminating power.** `opus5` is a fifth model at an *existing*
  tier. It sharpens the lineup picture and says nothing new about where the 25/55 cuts belong.

**Observed direction, recorded rather than acted on:** over-provisioning persists and, on the strong
tier, has widened — the newest strong model is quality-flat and 40% dearer than its predecessor on
this distribution, and five of seven tasks would have been served by the weak tier.

## Limitations / next

- **The bank still over-saturates.** Unchanged since 2026-06-16 and now the binding constraint on
  three separate questions (threshold placement, the oracle-coverage discount, the deferred
  efficiency study). The design of record is
  `docs/specs/2026-07-14-tier-separating-bank-design.md` — authored, not built, not run.
- **`fix-nonlocal-parse` is `indeterminate`, not `strong`.** Point estimate and interval disagree on
  the cheapest adequate tier at n=5, so even the one discriminating task does not deliver a clean
  empirical tier.
- **The `regression_test_present` gap is a single-bank observation** at n=30 per arm on a bank not
  designed to measure verification behavior. Directional.
- **Fable 5 (frontier)** not measured — opt-in, never score-assigned; deferred.

**Cost this round:** ≈ **$12.31** list-equivalent (Opus 5 arm, 35 trials), ≈ **$0 real** under
subscription auth; ceiling $70.00 against a $75 rail. The four cached arms replayed free.
Scorecard: `report/scorecard-model-tier-v1.md`.
