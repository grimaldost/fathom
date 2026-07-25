# Phase-2a findings — powered confirmatory run (2026-07-24)

558 trials planned, **331 completed** ($71.04); 227 lost to a **weekly account limit**
mid-run (see Missing data). Analysis is blind: `analyze_phase2.py` applied the
pre-registered gates from `docs/design/2026-07-24-dispatch-phase2-preregistration.md`
verbatim, with errored trials DROPPED as missing data (they never ran the agent).
Tiers: haiku-4.5, sonnet-5. Opus (Phase-2b) not yet run.

## Headline

**The SubagentStop verification gate is the first mechanism in this whole program to
clear its pre-registered gate decisively, on both tiers, with a large effect.**
Everything the prompt-time arms failed to do, an always-on gate on the subagent path
did.

## Results

### Subagent arm (e1-verif, footprint = regression_check_present)

| tier | bare-sub | gated-sub | lift | 90% CI (task-clustered) |
|---|---|---|---|---|
| haiku | 0.44 | **1.00** | **+0.56** | +0.44, +0.67 |
| sonnet | 0.44 | **1.00** | **+0.56** | +0.44, +0.67 |

**PROMOTE** (pre-registered: ≥+0.15 on ≥2 tiers). The CI does not cross zero on
either tier. Note `bare-sub` (0.44) sits *below* the bare main-agent rate
(0.48 haiku / 0.59 sonnet) on the same tasks — **delegating to a subagent slightly
degrades discipline**, and the gate more than recovers it.

### Band-B prompt-time arms (e1-*, 9 tasks x 3 repeats)

| arm | haiku | sonnet |
|---|---|---|
| bare | 0.48 | 0.59 |
| gate-4a | 0.52 (+0.04) | 0.78 (+0.19) |
| gate-placebo | 0.63 | 0.59 |
| oracle | 0.44 (−0.04) | 0.67 (+0.07) |
| classifier-hint | 0.63 (**+0.15**) | 0.85 (**+0.26**) |

### A3 (PRIMARY) — forced deliberation: **INCONCLUSIVE**

- haiku: gate-4a − bare = **+0.04** (90% CI −0.15,+0.22); − placebo = **−0.11** → refute-tier
- sonnet: gate-4a − bare = **+0.19** (90% CI −0.04,+0.41); − placebo = **+0.19** → promote-tier

One tier refutes, one promotes, and the promoting tier's CI crosses zero. Per the
pre-registration this is INCONCLUSIVE and we **stop** rather than re-run hunting for
significance. Opus is the pre-planned third tier that could settle the ≥2-tier rule.
Read plainly: after three runs (RG-2x2 +5/12, screen +0, here +0.04/+0.19), forced
deliberation has never produced a *replicable* effect. The prior is now weak.

### A1 — tier gradient

`classifier-hint` **replicates and is monotonic in tier** (+0.15 haiku → +0.26 sonnet),
matching the pre-registered capability-gating expectation and the screen's
strong-tier finding. It also beats the oracle on both tiers — naming the right skill
(oracle) does less than a short applicability hint. Baseline discipline rises with
tier (bare 0.48 → 0.59), consistent with the model-floor (Band-D) story.

### False positives

All measured null cells: **over_scope = 0.00 across every arm and both tiers**. No
prompt-time arm over-triggers on trivial edits. (Coverage caveat below.)

## Missing data (weekly account limit)

`c-debug`, `c-data`, `c-verif` (72 trials, the Band-C opus capability check),
`null-verif` (60), and 35 of `null-data`. Error detail on every one:
"You've hit your weekly limit · resets 12am (America/Sao_Paulo)". Errored trials cost
$0 and were dropped, not counted as failures. **Consequence:** Band-C is unmeasured
this phase, and the false-positive coverage is partial (null-debug complete,
null-data partial, null-verif absent).

**Correction to an earlier diagnosis:** the 17:42 halt was reported as an OAuth
refresh failure and I hypothesised a refresh-token rotation race. Re-auth did clear
it, but the *later* halt is unambiguously a weekly usage limit. The rotation
hypothesis was never confirmed and should not be carried forward as established.

## Construct-validity caveat on the subagent result (read before promoting)

The gate's injected text says "leave a check that would fail if it regressed … add
one now"; the measured criterion is `regression_check_present`. The gate therefore
names the behavior being measured — closer to a targeted instruction than a generic
discipline nudge, so **+0.56 is an upper bound on what a generic gate would yield**.
Two things keep it meaningful: (a) `bare-sub` received the identical task instruction
and still missed 56% of the time, so the gate changes real behavior, not just
scoring; (b) this is how the mechanism would actually ship — a verification gate that
says "verify" is not cheating, it is the design. But a fair next test is a
*differently-worded* gate, or a second discipline whose criterion the gate does not
name.

Also untested: the subagent arm never ran on the **null banks**, so the gate's
false-positive cost (does it force pointless checks on trivial edits?) is
**unmeasured**. That is the first thing to close before shipping it.

## Disposition

1. **Subagent gate — promote to a design track**, subject to the two tests above
   (differently-worded gate; null-bank false-positive). This is the strongest result
   the program has produced and it lands exactly on the user's multi-agent workflow.
2. **classifier-hint — confirmed, tier-graded.** Cheap, replicated twice now.
3. **Forced deliberation (4a) — do not build.** Three runs, no replicable effect.
4. **Band-C + null-verif — re-run when the weekly limit resets** (cheap: 132 trials,
   haiku+sonnet, ~$15).

## Provenance
`ledger-phase2/*.jsonl` (558 records) x `scripts-phase2/analyze_phase2.py`.
Pre-registration: craft `docs/design/2026-07-24-dispatch-phase2-preregistration.md`.
Cost: haiku $15.96 (279 runs, $0.057/trial), sonnet $55.09 (279, $0.197/trial).
