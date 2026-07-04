# humble-vs-super-v1 — first matrix (run notes)

- **Date:** 2026-06-14
- **Bank:** `humble-vs-super-v1`, dataset_version 1
- **Matrix:** 5 arms × 4 dev tasks × 5 repeats = **100 trials** (sealed holdout `fix-cache-eviction-bug` not run — excluded from `fathom run` by design, ADR-0005)
- **Arms:** `bare` · `humble-only` · `super-only` · `stack-humble` · `stack-super` (humblepowers 0.3.x · superpowers v5.1.0 @ `6fd4507` · held-constant stack = engineering-discipline + session-workflow)
- **Cost:** ~**$44** for the 100 trials (the `$2`/trial ceiling was 5× conservative). Whole project ≈ $85 incl. the $39 build + spikes.
- **Ledger:** `ledger/humble-vs-super-v1.jsonl`; scorecard `report/scorecard-humble-vs-super-v1.md`.

## Headline verdict

**On this bank, superpowers is the more *effective* plugin — it makes the agent write a regression test far more reliably than humblepowers — but it costs ~30–40% more to do so, and the two are within ~15% on quality-per-token. There is no decisive "humblepowers is more efficient" win: it is cheaper with a marginal token-efficiency edge, but lower discipline-reliability. Both plugins beat `bare`.** Directional, not statistically final (n=10 on the only discriminating criterion).

## The one criterion that discriminated

Ten of eleven verifier criteria sat at **100% across every arm** (the tasks were too easy on everything except one behaviour). The entire verdict rests on **`regression_test_present`** — did the agent write a test that fails on the original bug and passes on the fix — measured on the two bug-fix tasks (n=10/arm):

| Criterion | bare | humble-only | stack-humble | super-only | stack-super |
|---|---|---|---|---|---|
| fix_correct, no_regression | 100% | 100% | 100% | 100% | 100% |
| all feature edge-cases, tests_present, behavior_correct | 100% | 100% | 100% | 100% | 100% |
| **regression_test_present** | **0% (0/10)** | **50% (5/10)** | **60% (6/10)** | **90% (9/10)** | **100% (10/10)** |

→ `bare` **never** writes a regression test; humblepowers writes one ~half the time; **superpowers writes one almost always.** The ordering is consistent across both comparison pairs (`super-only` > `humble-only`; `stack-super` > `stack-humble`), which strengthens the directional read.

## Trial pass rate (all-criteria-true) + Wilson 95% CI

| Arm | Pass | Rate | Wilson 95% CI |
|---|---|---|---|
| bare | 10/20 | 50.0% | [29.9%, 70.1%] |
| humble-only | 15/20 | 75.0% | [53.1%, 88.8%] |
| stack-humble | 16/20 | 80.0% | [58.4%, 91.9%] |
| super-only | 19/20 | 95.0% | [76.4%, 99.1%] |
| stack-super | 20/20 | 100.0% | [83.9%, 100.0%] |

(The pass rate is driven entirely by `regression_test_present`: every feature trial passes for everyone, so pass-rate = 10 feature + the bug-fix trials that wrote the test.) **CIs overlap** (humble [53,89] vs super [76,99]) → the super > humble gap is **directional, not conclusive** at this n. fathom labels every arm "directional, not final."

## Economy & efficiency

| Arm | $/trial | turns/trial | tokens/trial | Quality / 100k tok |
|---|---|---|---|---|
| bare | $0.27 | 8.1 | ~117k | 0.28 |
| humble-only | $0.40 | 9.6 | ~198k | 0.29 |
| stack-humble | $0.42 | 8.9 | ~247k | **0.31** |
| super-only | $0.52 | 12.7 | ~228k | 0.28 |
| stack-super | $0.59 | 12.7 | ~294k | 0.26 |

- **Superpowers costs ~30–40% more** than humblepowers (`super-only` $0.52 vs `humble-only` $0.40; `stack-super` $0.59 vs `stack-humble` $0.42), using ~30% more turns and tokens.
- **Quality-per-token is roughly a wash, slight humble edge** (0.29–0.31 vs 0.26–0.28): superpowers buys its higher quality at a more-than-proportional token cost.
- **Pareto frontier (computed by hand):** `bare` (cheapest), `humble-only`, `super-only`, `stack-super` are non-dominated; **`super-only` dominates `stack-humble`** (95% at ~228k tok beats 80% at ~247k tok). The scorecard's ★ on `stack-humble` is therefore suspect — see caveats.

## Why (mechanism)

The result tracks the plugins' design philosophies. Humblepowers' **calibration doctrine** ("don't load a skill unless its benefit exceeds the context cost") means on a small bug-fix the model often judges the TDD/verification skill *not worth loading* — exactly the spike finding — so it fixes the bug and moves on without a regression test ~half the time. Superpowers is **more eager** (heavier skill set, `using-superpowers` meta-skill) and applies the discipline almost always. So humblepowers' lower regression-test rate is its design *working as intended* — judicious loading — which on this particular metric reads as a quality loss.

## Caveats / validity (important)

1. **Severe ceiling — only 1 of 11 criteria discriminated.** `fix_correct`, `no_regression`, and all feature criteria are 100% everywhere. The bank is far too easy except for the "write a regression test" behaviour. The verdict is narrow.
2. **n=10 bug-fix trials/arm → wide CIs → directional only.** super > humble is consistent but not statistically conclusive here.
3. **Efficiency Pareto-flag untrusted.** The efficiency view (PR09) shipped behind a *vacuous golden test* (the fixture was gitignored → self-bootstrapped → never compared); its ★ contradicts a hand-computed frontier. Trust the raw numbers, not the ★.
4. **Holdout not run.** A sealed-holdout pass would harden this.
5. **Operational noise:** the run hit two interruptions (subscription OAuth token expiry; background-process freezes on session suspend/resume) — recovered each time via fathom's idempotent resume. No trials lost.

## Bottom line (answering "is humblepowers more efficient than superpowers?")

**Not clearly.** On effectiveness, superpowers wins (regression-test discipline 90–100% vs 50–60%) at a ~30–40% cost premium. On pure token-efficiency they are within ~15% (slight humble edge). So it is a **quality-vs-cost trade, not an efficiency win for humblepowers**: superpowers buys real, reliable test discipline for proportionally more spend; humblepowers is cheaper and lighter but applies the discipline less often by design. If reliable regression tests matter, superpowers earns its cost here; if you are optimising context economy and accept ~half-the-time discipline, humblepowers is the leaner choice. **Both decisively beat doing nothing.**

The strongest follow-up is a **harder bank** (so `fix_correct`/`no_regression`/features aren't at ceiling) — only then does the comparison test more than a single behaviour.
