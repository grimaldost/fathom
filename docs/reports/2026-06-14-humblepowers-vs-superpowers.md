# Humblepowers vs Superpowers — A Scenario-Blind Tool-Effectiveness Evaluation

- **Date:** 2026-06-14
- **Author:** Grimaldo Stanzani (with Claude Opus 4.8)
- **Harness:** `fathom` — scenario-blind tool-effectiveness evals (bank `humble-vs-super-v1`, dataset_version 1)
- **Status:** Complete · 100/100 trials · directional result (see §7)
- **Artifacts:** ledger `ledger/humble-vs-super-v1.jsonl` · scorecard `report/scorecard-humble-vs-super-v1.md` · design spec `docs/specs/2026-06-14-fathom-humble-vs-super-design.md`

---

## Executive summary

Two process-discipline plugins for Claude Code were compared head-to-head on real coding tasks, scored blind,
and joined with economy (tokens, turns, USD). **Superpowers** (Jesse Vincent's `obra/superpowers`, 14 skills)
and **humblepowers** (a calibrated, trimmed 8-skill derivative) were each mounted into otherwise-identical
agents, against an unaided `bare` baseline.

The finding: on the one task behaviour that discriminated, **superpowers is more *effective*** — it makes the
agent write a regression test for a bug fix far more reliably (90–100% vs humblepowers' 50–60% vs bare's 0%) —
**but it costs ~30–40% more** tokens/dollars to do so, and the two plugins land within ~15% of each other on
quality-per-token. There is therefore **no decisive "humblepowers is more efficient" result**: it is the
cheaper, lighter option with a marginal token-efficiency edge but materially lower discipline-reliability.
**Both plugins beat doing nothing.** The result is directional (the bank discriminated on only one criterion,
n=10 per arm on that criterion), not statistically conclusive.

---

## 1. Background & motivation

Humblepowers is a process-discipline plugin (TDD, systematic debugging, verification-before-completion,
fit-ranked tool dispatch, brainstorming, planned execution) authored as a **calibrated derivative of
superpowers** — fewer skills, neutral register, and an explicit *dispatch doctrine*: load a discipline only
when its expected benefit exceeds its context-and-anchoring cost. The two are not meant to coexist
("never install both").

The practical question for anyone choosing between them: **does the trimmed, calibration-first humblepowers
actually deliver comparable or better outcomes than the heavier superpowers — and is it more efficient
per unit of cost?** That is a measurable, tool-effectiveness question, which is exactly what `fathom` exists to
answer.

## 2. Research question & hypotheses

> **RQ.** Inside an otherwise-identical Claude stack, does humblepowers produce better coding-task outcomes
> than superpowers, and at what economy (tokens / turns / USD)? Is humblepowers Pareto-better — equal-or-better
> quality at equal-or-lower cost?

**Pre-registered analysis (from the design spec, fixed before any trial ran):**
- **Binding contrast:** humble vs `bare` (large expected effect).
- **Exploratory contrast:** humble vs super (expected small; the continuous *economy* axis was expected to
  carry more signal than binary pass-rates given the achievable sample size).
- **Predicted discriminator:** `regression_test_present` / `no_regression` and token cost — process discipline
  was expected to show up as test-writing behaviour and as a token premium, not as raw fix-correctness.

## 3. Experimental design

### 3.1 The instrument — fathom

`fathom` runs real coding tasks under different **execution strategies / tool configurations** (called *arms*),
scores the results **blind to which arm produced them**, and joins quality with economy into a scorecard. Four
load-bearing invariants make the comparison trustworthy:

- **Blindness** — the grader (`verify.py`) receives only the final workspace (a stripped *result-view*) and
  carries no scenario/arm identity in its arguments or environment; economy data joins **after** scoring.
- **Append-only ledger** — every trial result is appended, never rewritten; reports regenerate from the
  ledger; runs resume idempotently on the key `(bank, dataset_version, task_id, config_hash, repeat)`.
- **Spawn isolation** — each agent runs under a credential-only temporary `CLAUDE_CONFIG_DIR`, **headless
  default-deny** (no `bypassPermissions`), with an explicit tool allow-list. No user config, CLAUDE.md, or
  history leaks into the supposedly clean arms.
- **config_hash** — every arm is identified by a SHA-256 over its fully-resolved configuration, **including the
  mounted plugin set** (each plugin's name, version, and a content tree-hash). Editing a plugin forks the
  longitudinal record rather than silently contaminating it.

### 3.2 The arms (the independent variable)

Five arms, **identical in every respect except the mounted plugin set** — same model (`claude-opus-4-8`),
effort (`high`), single-session strategy, tool allow-list (Read/Write/Edit/Glob/Grep/PowerShell/Bash, with the
`Task` subagent tool **allowed** so both plugins run as shipped), and per-task limits:

| Arm | Plugins mounted (via `--plugin-dir`) |
|---|---|
| `bare` | none (baseline) |
| `humble-only` | humblepowers (8 skills) |
| `super-only` | superpowers v5.1.0 @ `6fd4507` (14 skills) |
| `stack-humble` | humblepowers + engineering-discipline + session-workflow |
| `stack-super` | superpowers + engineering-discipline + session-workflow |

The `*-only` pair isolates the plugin; the `stack-*` pair embeds it in a realistic common stack
(engineering-discipline + session-workflow, **held constant** across both, so it cannot bias the humble↔super
contrast — only bound external validity). Plugins are mounted **as shipped** so their skills auto-trigger; a
real-spawn smoke check confirms the mount arms the agent (a canary skill appears in the spawn's init event only
when mounted).

### 3.3 The bank (the tasks)

Four stdlib-only Python tasks (plus a sealed holdout reserved, not run), each with a **blind verifier** that
emits per-criterion booleans:

| Task | Type | Criteria graded |
|---|---|---|
| `fix-offbyone-paginator` | bug-fix | `fix_correct`, `no_regression`, **`regression_test_present`** |
| `fix-tz-dst-normalize` | bug-fix | `fix_correct`, `no_regression`, **`regression_test_present`** |
| `feature-csv-coalesce` | feature | `behavior_correct`, `empty_input`, `ragged_rows`, `type_coercion`, `tests_present` |
| `feature-retry-backoff` | feature | `behavior_correct`, `zero_retry`, `jitter_bounds`, `error_propagation`, `tests_present` |
| `fix-cache-eviction-bug` | bug-fix (**sealed holdout**) | not run — reserved against task-design overfit |

The design grades **outcomes that a good *trajectory* leaves as an end-state fingerprint**, because fathom is
blind to trajectory. The sharpest such fingerprint is **`regression_test_present`**: the verifier takes the
candidate's new test, runs it against the *stashed original buggy source* (it must fail) and against the
candidate's fix (it must pass). Only an agent that actually practised test discipline leaves that mark.

### 3.4 The matrix & protocol

- **Matrix:** 5 arms × 4 tasks × 5 repeats = **100 trials** (repeats absorb LLM + skill-triggering
  nondeterminism). The sealed holdout is excluded from the run by design.
- **Gating protocol (followed in order):** `fathom smoke` (real-spawn isolation + mount gate — passed 8/8) →
  a 5-trial **cost-probe pilot** (confirmed arms run end-to-end and real cost ≈ $0.2–0.5/trial, far under the
  $2 ceiling) → the full matrix → `fathom report`.
- **Scoring:** verifier-first, per-criterion booleans; a trial "passes" only if **all** its criteria are true.
  Economy (tokens/turns/wall-clock/USD) is recorded per trial and joined after scoring.

## 4. Methodology notes (how trials actually execute)

Each trial: fathom builds a credential-only temp config, mounts the arm's plugins with repeatable `--plugin-dir`,
spawns one headless `claude -p` with the task instruction and the arm's tool allow-list (default-deny), captures
the economy from the streamed result, then runs the task's `verify.py` against the final workspace **locally and
offline** (stdlib-only tasks → no provisioning, deterministic grading). Plugins mounted this way **auto-trigger**
— the model decides whether to load each discipline, exactly as in real use, which is the point of testing the
plugin *as shipped* rather than force-injecting one skill.

## 5. Results

### 5.1 The only criterion that discriminated

Ten of eleven verifier criteria sat at **100% across all five arms** — every arm always fixed the bug without
regressions and always satisfied every feature edge-case. The entire between-arm difference is one criterion,
**`regression_test_present`** (bug-fix tasks, n=10/arm):

| Criterion | bare | humble-only | stack-humble | super-only | stack-super |
|---|---|---|---|---|---|
| `fix_correct`, `no_regression` (bug-fix) | 100% | 100% | 100% | 100% | 100% |
| all feature criteria, `tests_present`, `behavior_correct` | 100% | 100% | 100% | 100% | 100% |
| **`regression_test_present`** | **0% (0/10)** | **50% (5/10)** | **60% (6/10)** | **90% (9/10)** | **100% (10/10)** |

### 5.2 Trial pass-rate (all-criteria-true) with 95% confidence intervals

| Arm | Pass | Rate | Wilson 95% CI |
|---|---|---|---|
| bare | 10/20 | 50.0% | [29.9%, 70.1%] |
| humble-only | 15/20 | 75.0% | [53.1%, 88.8%] |
| stack-humble | 16/20 | 80.0% | [58.4%, 91.9%] |
| super-only | 19/20 | 95.0% | [76.4%, 99.1%] |
| stack-super | 20/20 | 100.0% | [83.9%, 100.0%] |

The pass-rate is fully explained by `regression_test_present`: all 10 feature trials pass for every arm, so an
arm's pass-rate = 10 + (bug-fix trials that wrote the regression test). The ordering **super > humble > bare is
consistent across both the `*-only` and `stack-*` pairs.**

### 5.3 Economy & efficiency (per trial)

| Arm | USD/trial | turns/trial | tokens/trial | wall (s) | Quality / 100k tok |
|---|---|---|---|---|---|
| bare | $0.27 | 8.1 | ~5.9k | 45 | 0.28 |
| humble-only | $0.40 | 9.6 | ~9.9k | 65 | 0.29 |
| stack-humble | $0.42 | 8.9 | ~12.4k | 56 | **0.31** |
| super-only | $0.52 | 12.7 | ~11.4k | 80 | 0.28 |
| stack-super | $0.59 | 12.7 | ~14.7k | 86 | 0.26 |

*(Whole matrix ≈ $44.03. "tokens/trial" counts cache-heavy input; the dominant economy currency is
tokens/turns — USD is a derived estimate, now flowing correctly after the D2 cost-flow fix.)*

**Pareto frontier (computed by hand from the table):** the non-dominated arms are `bare` (cheapest),
`humble-only`, `super-only`, and `stack-super`. **`super-only` Pareto-dominates `stack-humble`** — 95% quality
at ~11.4k tok beats 80% at ~12.4k tok. (fathom's scorecard flagged `stack-humble` ★, which is inconsistent with
this; see §7.3.)

## 6. Analysis & discussion

**Effectiveness — superpowers wins.** On the sole discriminating behaviour, superpowers writes the regression
test almost always (90% / 100%), humblepowers about half the time (50% / 60%), bare never (0%). The ~+20pp
pass-rate advantage of superpowers over humblepowers holds in both comparison pairs.

**Economy — humblepowers wins.** Superpowers spends ~30–40% more per trial (`super-only` $0.52 vs `humble-only`
$0.40; `stack-super` $0.59 vs `stack-humble` $0.42), with ~30% more turns and tokens — its larger skill corpus
is more context to carry and it does more work (it writes the test).

**Efficiency — roughly a wash, slight humble edge, but superpowers is not dominated.** Quality-per-token is
within ~15% (humble 0.29–0.31 vs super 0.26–0.28): superpowers buys its extra quality at a *more than
proportional* token cost. Yet `super-only` sits on the Pareto frontier (and dominates `stack-humble`), so it is
not an inefficient choice — it occupies the "more quality, more cost" corner of the frontier.

**Mechanism — the result is the design philosophy, observed.** Humblepowers' *calibration doctrine* ("don't
load a discipline unless its benefit beats its context cost") means that on a small, well-specified bug-fix the
model frequently judges TDD/verification *not worth loading* — the exact behaviour observed in a pre-experiment
spike, where a humblepowers-equipped agent declined to load TDD because "the task is small … not worth the
context cost." It then fixes the bug and stops, without a regression test, ~half the time. Superpowers is more
eager (heavier corpus, a `using-superpowers` meta-skill) and applies the discipline almost always.
**Humblepowers' lower score is its judiciousness working as intended** — which on *this* metric reads as a
quality loss, and which is precisely the trade it was designed to make.

**Adding the common stack** (engineering-discipline + session-workflow) nudged the regression-test rate up for
both families (+10pp each), consistent with python-engineering's testing emphasis; being common-mode, it does
not bias the contrast.

## 7. Threats to validity / limitations

1. **Severe ceiling — only 1 of 11 criteria discriminated.** `fix_correct`, `no_regression`, and every feature
   criterion were 100% for every arm. The tasks were too easy on everything except test-writing. The verdict is
   therefore **narrow** — it compares the plugins on a single behaviour, not on general coding effectiveness.
2. **Small n on the deciding criterion → directional only.** `regression_test_present` is measured on n=10/arm
   (2 bug-fix tasks × 5 repeats); the pass-rate CIs overlap (`humble-only` [53, 89] vs `super-only` [76, 99]).
   fathom labels every arm "directional, not final." The consistency across both pairs strengthens the direction
   but does not make it statistically conclusive.
3. **The efficiency Pareto-flag is untrustworthy.** The efficiency view shipped behind a *vacuous golden test*
   (its fixture was accidentally gitignored, so the test self-bootstrapped and never compared) — caught and
   fixed during verification of the build, but the Pareto-flag logic itself remains unverified, and its ★ on
   `stack-humble` contradicts the hand-computed frontier. Trust the raw numbers, not the flag.
4. **Holdout not run.** The sealed `fix-cache-eviction-bug` was reserved against task-design overfit and would
   harden the result; it is excluded from the standard run.
5. **Triggering not measured directly.** This evaluates the plugin *as shipped* (auto-trigger included), so the
   result blends "the discipline's content" with "how often the dispatch loads it." That blend is intentional —
   it is what a user experiences — but it means a low score can reflect under-triggering rather than weak
   guidance (which, for humblepowers, is by design).
6. **Operational noise (no effect on data).** The run hit a subscription-token expiry and two
   background-process freezes (session suspend/resume); each was recovered via fathom's idempotent resume with no
   trials lost or double-counted.

## 8. Conclusion

**Is humblepowers more efficient than superpowers? Not clearly — and on raw effectiveness it is behind.** On
the one behaviour this bank could measure, superpowers is the more reliable disciplinarian (writes a regression
test 90–100% of the time vs humblepowers' 50–60%), at a ~30–40% cost premium; on quality-per-token the two are
within ~15%, a slight edge to humblepowers but not a Pareto win for it (`super-only` is non-dominated). The
honest framing is a **quality-versus-cost trade, not an efficiency victory for either side**:

- If reliable regression-test discipline matters to you, **superpowers earns its higher cost here.**
- If you are optimising context economy and accept the discipline firing ~half the time on small tasks,
  **humblepowers is the leaner choice** — and its lower score is its calibration philosophy operating as
  designed, not a defect.
- **Both decisively beat an unaided agent** (0% regression-test discipline).

This is a real, reproducible signal — but a *thin* one, resting on a single criterion at modest sample size.

## 9. Future work (highest-leverage first)

1. **A harder bank.** The dominant limitation is the ceiling. Tasks where `fix_correct`/`no_regression`/feature
   criteria are *not* automatic would let the plugins separate on more than one behaviour and give the contrast
   real statistical teeth.
2. **Run the sealed holdout** and add repeats on the discriminating criterion to tighten the CIs.
3. **Light up the dark-shipped pairwise judge** for an architecture/readability quality axis beyond mechanical
   verifier checks (with the blindness scrub the build added).
4. **Measure triggering directly** (`evaluate-skill`) to separate "did the right discipline fire" from "was its
   content good" — the two halves this experiment deliberately blends.

---

## Appendix A — reproducibility

```sh
uv run fathom smoke                                                                 # 8/8 isolation + mount gate
uv run fathom run humble-vs-super-v1 --scenarios-dir scenarios/humble-vs-super --dry-run --repeats 5
uv run fathom run humble-vs-super-v1 --scenarios-dir scenarios/humble-vs-super --repeats 5   # 100 trials, resumable
uv run fathom report humble-vs-super-v1                                             # regenerate the scorecard
```

- **Subjects:** humblepowers 0.3.x · superpowers `obra/superpowers` v5.1.0 commit
  `6fd4507659784c351abbd2bc264c7162cfd386dc` (both vendored under `tasks/humble-vs-super-v1/plugins/`).
- **Apparatus build:** the bank, arms, and report extensions were built as an 11-PR governed series
  (`pr-series/humble-vs-super/`), spec certified through the keel Definition-of-Ready gate with a two-round
  blind pre-mortem (`docs/specs/2026-06-14-fathom-humble-vs-super-design.md`).
- **Cost:** ~$44 for the 100 trials; ~$85 including apparatus build and spikes.

## Appendix B — full per-criterion table

| Criterion (applies to) | bare | humble-only | stack-humble | super-only | stack-super |
|---|---|---|---|---|---|
| behavior_correct (feature) | 100% | 100% | 100% | 100% | 100% |
| empty_input (csv) | 100% | 100% | 100% | 100% | 100% |
| ragged_rows (csv) | 100% | 100% | 100% | 100% | 100% |
| type_coercion (csv) | 100% | 100% | 100% | 100% | 100% |
| zero_retry (backoff) | 100% | 100% | 100% | 100% | 100% |
| jitter_bounds (backoff) | 100% | 100% | 100% | 100% | 100% |
| error_propagation (backoff) | 100% | 100% | 100% | 100% | 100% |
| tests_present (feature) | 100% | 100% | 100% | 100% | 100% |
| fix_correct (bug-fix) | 100% | 100% | 100% | 100% | 100% |
| no_regression (bug-fix) | 100% | 100% | 100% | 100% | 100% |
| **regression_test_present (bug-fix)** | **0%** | **50%** | **60%** | **90%** | **100%** |
