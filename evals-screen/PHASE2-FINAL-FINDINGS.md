# Phase-2 final findings — powered confirmatory run (2026-07-24/25)

**648 completed trials, $113.09**, tiers haiku-4.5 + sonnet-5. Blind analysis:
`analyze_phase2.py` applied the gates from
`docs/design/2026-07-24-dispatch-phase2-preregistration.md` verbatim; errored trials
(weekly-limit casualties, later refilled) dropped as missing data. Supersedes
PHASE2A-FINDINGS.md, whose "missing data" section is now closed.

## Headline

**An always-on gate on the subagent path is the one mechanism that works — but only
when it states the discipline rather than prescribing the artifact.** The
pre-registered false-positive constraint killed the variant that scored highest on
the primary metric. Without the null banks we would have shipped the harmful one.

## The decisive table

| arm | footprint haiku | footprint sonnet | false-positive (both tiers) | verdict |
|---|---|---|---|---|
| `bare-sub` (no gate) | 0.44 | 0.44 | 0.00 | baseline |
| `gated-sub` (**prescriptive** wording) | **1.00** (+0.56) | **1.00** (+0.56) | **0.58** | **REJECTED — over-triggers** |
| `generic-sub` (**discipline** wording) | 0.67 (+0.22) | **1.00** (+0.56) | **0.00** | **PROMOTE** |

- Prescriptive gate: *"…leave a check that would fail if it regressed. If you have not
  added a regression check … add one now."*
- Discipline gate: *"…are you actually confident this is correct, or are you assuming
  it is? … satisfy yourself that it genuinely works and that you would find out if it
  stopped working."* — names no artifact, no "check"/"test"/"regression".

The prescriptive gate hits 1.00 footprint by ordering the behavior unconditionally —
and then performs it on **58% of trivial edits** (writing tests for a docstring bump).
It is not applying judgment; it is obeying. The discipline gate lifts real behavior
with **zero** false positives on either tier: it discriminates.

**Delegation itself degrades discipline.** `bare-sub` (0.44) sits below the bare
main agent on the same tasks (0.48 haiku / 0.59 sonnet). Handing work to a subagent
loses discipline that the parent would have applied; the gate recovers it.

## The rest of the matrix

### A3 (PRIMARY) — forced deliberation: **INCONCLUSIVE, prior now weak**

| tier | vs bare | 90% CI | vs placebo | tier verdict |
|---|---|---|---|---|
| haiku | +0.04 | −0.15, +0.22 | −0.11 | refute |
| sonnet | +0.19 | −0.04, +0.41 | +0.19 | promote |

One tier each way, and the promoting tier's CI crosses zero. Pre-registration says
report and **stop**, not re-run for significance. Across three runs (RG-2×2 +5/12,
screen +0, here split) forced deliberation has never replicated. **Do not build it.**

### A1 — selection arms

| arm | haiku | sonnet |
|---|---|---|
| `classifier-hint` (applicability hint) | **+0.15** | **+0.26** |
| `oracle` (names the exact right skill) | −0.04 | +0.07 |

`classifier-hint` replicates a third time and is monotonic in tier. It **beats the
oracle on both tiers**: a short "this situation calls for X-type care" outperforms
naming the correct skill. Baseline discipline rises with tier (0.48 → 0.59) — the
model-floor story holds. Both arms: 0.00 false positives.

### Band-C — emergent need: **nothing moves it** (now measured, n=18/cell)

| tier | bare | oracle |
|---|---|---|
| haiku | 0.50 | 0.50 (+0.00) |
| sonnet | 0.50 | 0.44 (−0.06) |

Confirms the screen at better power: when the need arises mid-execution rather than in
the prompt, telling the model the right skill does **nothing**. Band-C is
capability-bound, not dispatch-bound. This is the clearest statement yet that
selection ≠ incorporation.

### False positives — prompt arms

Every prompt-time arm, both tiers, n=18/cell: **0.00**. None over-triggers on trivial
edits. The over-trigger risk is specific to the *prescriptive gate*.

## What this means

1. **Ship the discipline-worded subagent gate.** It is the only mechanism in the whole
   program that lifts behavior on both tiers with no false-positive cost. It targets
   exactly the user's real workflow (opus main session + heavy delegation).
2. **Never prescribe the artifact in an always-on gate.** The same mechanism, worded
   as an instruction instead of a discipline, becomes a noise generator. This
   generalizes to the convoy design (track E): a mandatory stage should require
   *verification*, not *a test file*.
3. **Stop pursuing prompt-time dispatch for Band C.** Two runs agree it is
   capability-bound.
4. **`classifier-hint` is the cheap prompt-time win** where dispatch is possible at
   all (Band B), and it beats the oracle — worth folding into the router work.

## Honest limits

- **Single discipline for the gate arms.** Both gates were tested only on
  verification-before-completion (e1-verif / null-verif / null-debug). Whether a
  discipline-worded gate helps for systematic-debugging or data-engineering is
  untested.
- **`generic-sub` haiku is +0.22, not +0.56.** The discipline wording is weaker on the
  weak tier — a strong-tier model does more with a general prompt. Expect tier
  dependence in production.
- **No opus tier.** Phase-2b was not run. A3's ≥2-tier rule remains formally unsettled,
  and the gate is unmeasured on the tier the user actually runs.
- **n=9–12 per subagent cell.** The effects are large and the CIs exclude zero, but
  these are small cells; the false-positive contrast (0.58 vs 0.00) is the robust part.

## Provenance
`ledger-phase2/*.jsonl` (648 completed) × `scripts-phase2/analyze_phase2.py`.
Cost: haiku $25.44 (407 runs, $0.063/trial), sonnet $87.65 (408, $0.215/trial).
Gate plugins: `scenarios/phase2-hooks/subagent-{verify,generic}-gate/`.
