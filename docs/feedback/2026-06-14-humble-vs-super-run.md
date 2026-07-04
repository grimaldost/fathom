# fathom feedback — first real paid matrix (humble-vs-super-v1)

- **Date:** 2026-06-14
- **Tool/version:** fathom 0.1.0
- **Context:** First end-to-end **paid** run of a full fathom analysis: bank `humble-vs-super-v1`, 100 trials,
  5 plugin-mount arms, blind verifier-first grading, economy join, scorecard. Exercised `fathom smoke`,
  `fathom run` (with `--dry-run`, `--repeats`, `--limit`, and idempotent resume), and `fathom report`.
- **Outcome:** The spine worked under real conditions and **survived two mid-run interruptions with zero lost
  trials** — but the run also exposed one real efficiency-view bug, confirmed the ceiling limitation with hard
  data, and surfaced an operational token-TTL friction.

## What worked

- **Idempotent resume is the hero (ADR-0002 validated under fire).** The run hit a subscription OAuth-token
  expiry mid-matrix (47/100) *and* two background-process freezes (session suspend/resume). Each time, killing
  the stale process and re-invoking `fathom run` resumed cleanly from the ledger — **no trial lost, none
  double-counted, no manual bookkeeping.** This is the append-only + resume design paying for itself.
- **The cost-probe pilot pattern worked.** A 5-trial `--limit` pilot predicted ~$0.2–0.5/trial; the full matrix
  landed at ~$0.27–0.59/trial — the $2/trial ceiling was 5× conservative, and the pilot caught that *before*
  the full spend. Keep this as the standard pre-matrix step.
- **The new mount/available smoke check (PR05) works on real spawns** — `fathom smoke` passed 8/8 including the
  canary-skill-in-init-event assertion (treatment armed) and its absence in the control. The `--plugin-dir`
  mount mechanism is proven, not assumed.
- **D2 is fixed and confirmed live** — `cost_usd_est` flowed all the way to the scorecard's economy/efficiency
  columns (non-zero USD), via the token×price estimate on subscription auth.
- **The `regression_test_present` swap-verifier is excellent** — a clean, deterministic, blind signal (run the
  candidate suite on the buggy original; red ⇒ a real bug-covering test). It was the *one* criterion that
  discriminated, and it did so unambiguously.

## Friction

- **[MED] An hours-long matrix outlasts the subscription OAuth token's TTL.** The 100-trial run (~hours) hit a
  `401` mid-way; the token had been valid for the pilot + 47 trials, then lapsed. fathom classifies it correctly
  (infrastructure, stop the matrix), but recovery required a manual re-auth + re-run, twice.
- **[LOW] `fathom report` rejects `--scenarios-dir`** while `fathom run`/`--dry-run` *require* it — a CLI asymmetry.
  (report re-derives arm names from the ledger's `scenario` field, so it doesn't need it — but the inconsistency
  reads as a bug for a moment.)

## Misses

- **[HIGH] phase: review/gate — the efficiency-view Pareto flag is wrong, and shipped unverified.** The
  scorecard ★-flags `stack-humble` as Pareto-optimal, but a hand-computed frontier shows **`super-only`
  dominates `stack-humble`** (95% pass at ~11.4k tok/trial beats 80% at ~12.4k tok/trial — more quality, fewer
  tokens). Either the Pareto logic is incorrect or ★ silently means "highest quality-per-token ratio" rather
  than "non-dominated"; either way it is misleading. **Root cause it slipped through:** this view (PR09) shipped
  behind a *vacuous golden test* — the golden fixture `tests/fixtures/report/golden-scorecard.md` was matched by
  an over-broad `report/` gitignore rule, so it was never tracked, the test self-bootstrapped in every fresh
  worktree, and the Pareto logic was never actually asserted. (Both the gitignore and the consumer's vacuous
  `pass_pattern=" passed"` pytest gate were caught + fixed during post-run verification — commit `fb1dc38`; the
  pytest-gate semantics are routed to the series engine.)
- **[MED] phase: task authoring — the bank ceilinged on 10 of 11 criteria.** `fix_correct`, `no_regression`,
  and every feature criterion were 100% across all five arms; only `regression_test_present` varied. The
  100-trial / ~$44 experiment effectively measured one behaviour. Confirms `STATUS.md` next-step #1 ("a
  discriminating v2 bank") with hard data — the tasks must be hard enough that `bare` *sometimes fails* the
  correctness criteria, not just the discipline criterion.

## Vacuous gates

- **Two, both now fixed.** (1) The golden-scorecard test self-bootstrapped because its fixture was gitignored
  (fathom) — fixed in `fb1dc38` by anchoring the rule to `/report/` and tracking the fixture. (2) The build
  series' pytest quality gate used `pass_pattern=" passed"`, which matches `"1 failed, N passed"` (series engine gate
  semantics) — hardened in `fb1dc38` and routed to the series engine report. Both had hidden a real failing test.

## Proposed promotions / changes

1. **[HIGH]** Fix and **actually test** the efficiency-view Pareto flag (`src/fathom/report.py`): compute the true
   non-dominated frontier (≥ quality AND ≤ tokens), and — now that the golden fixture is tracked — assert the
   efficiency table in the golden so the logic can't regress unseen again.
2. **[MED]** Add a **token-TTL pre-flight** to `fathom run`: estimate the matrix wall-clock (from the pilot or
   prior runs) and, if it plausibly exceeds the subscription token's remaining validity, warn "re-auth before
   launching" — or support chunked auto-resume. Turns two manual recoveries into zero.
3. **[MED]** Promote `STATUS.md` next-step #1 from hypothesis to **confirmed**: build a v2 bank whose correctness
   criteria are not at ceiling, so the quality axis carries more than one behaviour's worth of signal.
4. **[LOW]** Let `fathom report` accept `--scenarios-dir` (or document that it re-derives arm names from the
   ledger), for CLI symmetry with `run`.

## Cost

| Stage | Trials | Cost |
|---|---|---|
| smoke (×3 across the run) + cost-probe pilot | 5 + gates | ~$2 |
| full matrix | 100 | **~$44** ($0.27–$0.59/trial by arm) |

Whole eval ≈ $44; whole project (incl. the $39 apparatus build + spikes) ≈ $85, against a $200+ printed ceiling.
