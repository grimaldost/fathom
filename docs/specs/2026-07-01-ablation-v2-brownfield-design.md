# Series engine value-side ablation v2 -- brownfield instrument (design)

- **Date:** 2026-07-01
- **Status:** design; instrument built + validated; difficulty probe in progress
- **Bank:** `tasks/ablation-v2/` (`exprlang`)
- **Supersedes (as the value-side design):** `2026-07-01-pr-pilot-full-ablation-design.md`
  (v1/querytable), which produced a quality-null.

## Pre-mortem amendments (folded 2026-07-01)

A fresh-eyes pre-mortem (keel:pre-mortem-review) returned NOT CERTIFIED (2 BLOCKER,
4 MAJOR, 2 MINOR). The probe then confirmed the central risk empirically: bare Sonnet 5
= 6/6 on this brownfield task at ~24 turns/trial -- it self-verifies in-session. Folded:

- **FM-1 (BLOCKER, self-gating confound).** At Sonnet-5-high with tools + tests present,
  bare self-gates, so bare-vs-bare-gate measures "forced extra turns," not gate value.
  RESOLUTION: the PRIMARY gate-value measurement is now the **weak tier (Haiku)** cross
  plus a **low-effort Sonnet** pair (`sonnet-lo` / `sonnet-lo-gate`) -- regions where the
  model does not reliably self-verify. Both are fair to bare (identical model+effort).
  The Sonnet-5-high harness row is kept but DEMOTED to "expected ~null; documents the
  self-gating result." Rejected as unfair: no-tests-for-gated-arms-only, or lowering
  bare's effort below its own gate arm.
- **FM-6 (MAJOR, extra-spawn confound).** Gated arms get extra spawns the bare arm never
  gets, so lift could be "N tries beat 1." RESOLUTION: added a **reprompt-session**
  strategy -- an iteration-matched control (impl + one UNCONDITIONAL generic re-verify
  spawn, no gate info). Arms `haiku-reprompt` / `bare-reprompt`. Gate INFORMATION is then
  (gate - reprompt); mere extra iteration is (reprompt - bare).
- **FM-4 (MAJOR, subset-proper unverified).** RESOLUTION: mutation validation run. Of
  four defect classes, THREE escape the visible gate but are caught by the oracle
  (no-or-short-circuit -> `or_short_circuit`; bool-is-int -> `type_bool_in_arith` /
  `type_compare_bool`; and/or-precedence -> `precedence`) and one is gate-caught
  (single-char-lex). The visible gate is a PROPER subset; defect-escape is real and
  per-class calibrated.
- **FM-2 (BLOCKER, phantom arms).** RESOLUTION: every arm now has a scenario file
  (13 total). `bare-authoring` + `haiku-authoring` built with an injected brief
  (`scenarios/ablation-v2/authoring-brief.md`, absolute path). `sonnet` == `bare` (alias,
  no phantom file). `pp-series` is explicitly DEFERRED and not claimed from (Engine note).
- **FM-3 (MAJOR, power).** RESOLUTION: n pinned per phase -- Haiku cross n=10, mid/opus
  n=8. Report Wilson 95% CIs and the minimum detectable effect; widen n if a gap is
  borderline. (n=10 separates ~0.4 vs ~0.85 but is marginal for smaller gaps.)
- **FM-5 (MAJOR, all-or-nothing pass).** RESOLUTION: the ledger already stores all 15
  per-criterion booleans per trial; the report presents per-criterion pass vectors +
  defect-escape PER CLASS as primary, not just the 15-way AND.
- **FM-7 (MINOR, generalization).** RESOLUTION: conclusions hard-scoped to "one
  brownfield interpreter feature-add of this size"; no lineage-wide phrasing in §10 or
  the report.
- **FM-8 (MINOR, review no-op).** RESOLUTION: review arms keep the identical
  `Bash(python:*)` allowlist so a review CAN re-run tests; a review-null is flagged as
  instrument-ambiguous, not proof of no value.

### Engine (pp-series) decision

By the self-gating argument the engine's incremental QUALITY on a self-checkable task is
expected to be null for the same reason the gate's is; its value is operational
(isolation, attention, governance) and its ~8x cost was already measured (2026-06-10).
Plan: complete the non-engine matrix first, then OPTIONALLY run a small `pp-series` batch
(n~4) on exprlang for a current-lineup cost/economy datapoint and a quality-parity check
-- NOT to claim incremental quality. Series assets + auto-mode bypassPermissions handling
are prerequisites; if not run, the report says so and draws no engine conclusion beyond
the existing cost prior.

## 1. Objective

Measure whether the series engine's **engine-independent** functionalities and the **model-tier
ladder** produce measurable quality lift on the current Claude lineup, and locate the
region where they do. "Engine-independent" = everything that is NOT the headless
orchestration engine: the deterministic quality **gate** + bounded fix loop, the
structured **review** pass, and the prompt/context **authoring** the skills provide.

## 2. Why v1 was a quality-null (the diagnosis that drives v2)

The v1 task (`querytable`) was **greenfield** (the candidate wrote one module,
`core.py`, from scratch) and **single-file**. Bare Sonnet 5 scored 5/5 three times.
Two structural reasons it could not discriminate the arms:

1. **No regression surface.** The gate's central value is catching a change that
   breaks *existing* behaviour. A greenfield task has no existing behaviour to break,
   so the gate has nothing to catch that the model's own pass would not.
2. **No cross-file coupling.** A single-file task cannot exhibit the "fix one site,
   forget the mirror" defect that multi-file changes produce.

So the null was an **instrument** limitation, not evidence that the features add no
value. Concluding "features add +0" from it would be concluding from a blunt
instrument. v2 fixes the instrument.

## 3. The reframing: induce *premature satisfaction*, do not chase "too hard"

The series engine's thesis is not "the model cannot do it." It is: *the model, self-judging in
a single pass, sometimes declares done prematurely -- it skips full verification,
regresses existing behaviour, or misses an edge cluster -- and a deterministic harness
prevents that.* The discriminating task must therefore be one where a plausible,
self-judged solution is **reliably incomplete or regressive**, while the *same model*
with forced verification + bounded iteration converges. Model capability is held
constant across arms; the only variable is harness discipline.

## 4. The instrument: `exprlang` (brownfield, multi-file)

An existing expression-language package the candidate must EXTEND:

- `exprlang/lexer.py`, `parser.py`, `evaluator.py`, `errors.py` -- today it evaluates
  int/float arithmetic (precedence, unary minus, parens, variables,
  division/modulo-by-zero errors), with a comprehensive **green baseline suite**
  (`tests/test_arithmetic.py`).
- **Change requested:** add comparison (`== != < <= > >=`) and boolean (`and or not`,
  `true`/`false`) operators, with a specified precedence table, left-associativity,
  short-circuit `and`/`or`, and type rules.

The subtleties that induce premature satisfaction (all stated plainly in the spec, so
the failure is under-implementation/under-testing, not under-specification):

- **Short-circuit error-suppression** -- `false and (1/0 > 0)` must return `False`, not
  raise; the naive eager evaluator raises. Easy to miss, especially for `or`.
- **bool-is-a-subclass-of-int** -- `true + 1` must be a type error. A candidate that
  validates numeric operands with `isinstance(x, (int, float))` wrongly accepts bools.
  The classic Python trap.
- **Multi-char operator lexing (maximal munch)** -- `<=`/`>=`/`==`/`!=` must lex as one
  token; a candidate extending only single-char lexing breaks them.
- **Precedence** -- new operators slot BELOW arithmetic; a careless parser edit
  regresses existing arithmetic precedence (the baseline suite guards it).
- **Cross-file coupling** -- the feature touches lexer + parser + evaluator + errors;
  forgetting any one file fails.

### 4.1 Visible gate is a proper subset of the blind oracle

- **Visible gate** (present in the repo for ALL arms; `tests/`): baseline arithmetic
  (regression guard) + PARTIAL feature tests. Deliberately omits: `or` short-circuit,
  the bool-is-int cases, the full precedence cross-product, and property testing.
- **Blind oracle** (`verify.py`, harness-side, grades every arm): everything the gate
  covers PLUS `or` short-circuit, bool-is-int, full precedence, and **property-random**
  (60 generated ASTs, fully parenthesized, vs an independent reference evaluator).

Consequence: passing the gate does NOT guarantee passing the oracle. The gap is the
**defect-escape** surface -- what a forced gate cannot catch but a review pass might.

## 5. Arms (two axes on one instrument)

### Harness axis (model fixed = `claude-sonnet-5`)

| arm | strategy | what it isolates |
|-----|----------|------------------|
| `bare` | single-session | plain Claude, self-judged (baseline) |
| `bare-gate` | gated-session | + deterministic full-suite gate + bounded fix loop |
| `bare-gate-review` | gated-review | + one structured review pass after gate-green |
| `bare-authoring` | single-session + injected context | + series-engine-style structured brief (scope/plan), no engine |
| `pp-series` | series | the full headless engine (cost + quality reference) |

### Tier axis (harness fixed = bare single-session)

| arm | model | what it isolates |
|-----|-------|------------------|
| `haiku` | claude-haiku-4-5 | weak tier on a task with headroom |
| `sonnet` | claude-sonnet-5 | mid tier (shared cell with `bare`) |
| `opus` | claude-opus-4-8 | strong tier -- does it actually beat Sonnet here? |

The tier axis answers the over-provisioning / tier-by-difficulty question on an
instrument that (unlike `model-tier-v1`) actually has failure headroom.

## 6. Fairness constraints (so each arm isolates what it claims)

- **Same repo + same tools for every arm.** The tests are in the repo for `bare` too;
  the difference is only whether the harness *forces* the run + iteration. This
  measures "forced discipline vs. the model's own judgement," which is the series engine's real
  claim -- not "did we tell it tests exist."
- **The gate the disciplined arms run is the VISIBLE suite**, never `verify.py`. The
  blind oracle grades all arms identically afterward.
- **Generous timeouts** (1800s/trial, 120 turns) so a long-but-legitimate solve is
  never truncated into a false failure.

## 7. Metrics

- **Blind-oracle pass rate** per arm (primary), n>=10/cell.
- **Defect-escape rate** = trials where the visible gate is green but `verify.py` is red
  (recoverable from `TrialResult.detail` "gate first/final" + oracle outcome).
- **Marginal lift**: bare -> +gate -> +review; bare -> +authoring; each vs `pp-series`.
- **Tier discrimination**: haiku vs sonnet vs opus pass rate.
- **Economy**: sessions/trial, wall-clock, token/$ (subscription -> ~$0 real; report
  list-price equivalent).

## 8. Difficulty calibration (the probe)

Before the matrix, probe `bare` alone (n=6). Target pass rate strictly in (0,1),
ideally 40-70%. If bare aces (~100%) escalate difficulty; if it floors (~0%) ease it.
Record each probe outcome + cost. Only spend on the matrix once the instrument
discriminates.

## 9. Threats to validity (for the pre-mortem to attack)

- **Grader risk.** `verify.py`'s reference evaluator could be wrong; mitigated by the
  bank-validation gate (the correct solution passes all 15 criteria, incl. 60
  property cases) -- but the reference should still be adversarially reviewed.
- **Gate == oracle leakage.** If the visible suite were as strong as the oracle,
  `bare-gate` would trivially ace and review would show no lift. The subset design
  prevents this, but the *degree* of subset matters and should be sanity-checked.
- **bare arm information environment.** Is it fair that bare "could" run the tests but
  might not? Yes -- that is the measured variable. But the prompt must not *tell* bare
  to skip verification; it currently says nothing about the harness, only the task.
- **Review-arm contamination.** The review prompt must not leak oracle specifics; it is
  generic ("review for correctness against the task").
- **Single-task generalization.** One task family (an interpreter feature) is a narrow
  slice; conclusions are scoped to "brownfield multi-file feature-add of this size."
- **Stochasticity.** n>=10 needed to separate, say, 50% from 80%; report CIs.

## 10. Decision rules (what each result means)

- **Ladder appears** (bare < +gate <= +gate+review, with defect-escapes at bare): the
  engine-independent discipline adds measurable value on brownfield work -> the series engine's
  gate/review earn their keep here; quantify the lift.
- **+authoring > bare** with no gate: the skills' prompt-structuring alone helps.
- **pp-series ~ +gate+review on quality but much costlier**: the engine's value is
  operational (isolation/attention), not incremental quality -- consistent with prior
  findings; state it plainly.
- **Flat (all arms ~ bare)** even here: strong evidence the features add little
  incremental quality even on brownfield multi-file work -> the honest, now
  well-instrumented negative (very different from the v1 null).
- **Tier axis flat** (opus ~ sonnet): over-provisioning persists even with headroom.
  **Tier axis separates** (opus > sonnet > haiku): the ladder is justified where
  difficulty is real.
