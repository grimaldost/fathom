# Findings — multiagent dispatch with convoy's gate versus multiagent dispatch alone (iteration 1)

[experiment-rigor | measurement -> experiments/multiagent-composition-v2/record.yaml]

**Status: closed 2026-09-03.** The derived report
[`experiments/multiagent-composition-v2/report.md`](../../experiments/multiagent-composition-v2/report.md)
is the source of every number below (it is rendered from `record.yaml` and gated for drift);
this document explains, points, and records what the numbers cannot say.

## The question

Does a Sonnet orchestrator dispatching one implementer subagent per PR produce more
held-out-clean work when convoy's standalone gate — fail-closed independent checks and a
repair brief — runs between PRs than when it verifies with the project's own suite alone?
And is the gain the independent information (gate arm > placebo arm), not the extra
iteration a ceremony gate also buys (placebo ≈ control)? Convoy's orchestration appears in
no arm.

## Method, in one paragraph

Bank `multiagent-composition-v2`: one five-PR feature (comparison and boolean operators for
a small expression language) whose PR prompts state *what* to build but not the type rule
the held-out oracle checks. Eight cells: four arms (control, placebo, perpr, final) × two
implementer tier-sets (Haiku, Sonnet); the orchestrator is Sonnet 5 at effort high in every
arm; tools, limits and env keys are identical across arms and the injected briefs differ in
one contiguous block. Primary endpoint `held_out_clean`: all six held-out criteria in
`verify.py` pass on the executed workspace, none of them asserted by any gate check or
probe. Four pre-registered one-sided Fisher contrasts per tier-set, Holm-corrected within
the tier-set; Wilson 95% intervals on every cell; tier-sets never pooled. n = 16 per cell
(the first three repeats are the pooled pilot; thirteen arm-interleaved repeat passes
follow). Pre-registration: `docs/specs/2026-09-01-multiagent-composition-preregistration.md`
and its dated addenda; frozen record: `experiments/multiagent-composition-v2/record.yaml`.

## Results

`held_out_clean`, numerator/denominator and Wilson 95%, Haiku implementers then Sonnet:

| arm | Haiku | Sonnet |
|---|---|---|
| control (own suite only) | 4/16 [0.10, 0.49] | 2/16 [0.03, 0.36] |
| placebo (ceremony gate, no information) | 6/16 [0.18, 0.61] | 5/16 [0.14, 0.56] |
| perpr (convoy gate after each PR) | 16/16 [0.81, 1.00] | 14/16 [0.64, 0.97] |
| final (convoy gate once, after the session) | 12/16 [0.51, 0.90] | 9/16 [0.33, 0.77] |

Pre-registered contrasts (one-sided Fisher, Holm-adjusted within the tier-set's family of
four, alpha 0.05):

| contrast | Haiku | Sonnet |
|---|---|---|
| perpr > control | < 0.0001 | 0.0001 |
| **perpr > placebo (decisive)** | **0.0004** | **0.0048** |
| final > control | 0.0121 | 0.0233 |
| final > placebo | 0.0366 | 0.1426 (not significant at the achieved n) |

Seven of the eight contrasts clear Holm at both tiers; the one that does not is the
post-session gate against the placebo at the Sonnet tier, where the declared power on a
final-arm contrast was never high (the power calculation was made on the per-PR gap).

**Sensitivity endpoint** (`held_out_clean_independent`: the four criteria the probes' type
rule never touches, exploratory, outside the Holm family): control 4/16 and 2/16, placebo
7/16 and 5/16, perpr 16/16 and 14/16, final 13/16 and 10/16; perpr > placebo one-sided
p = 0.0004 and 0.0016. The effect is not carried by the two criteria nearest the probe.

**Project-visible surface** (`full15_clean`, exploratory): control 4/16 and 2/16, placebo
6/16 and 5/16, perpr 16/16 and 14/16, final 14/16 and 12/16. The implementer's own suite
does not separate the arms the way the held-out oracle does; a green own-suite is not what
the gate adds.

**Mechanism, attested from transcripts and ledger detail.** The post-session gate went red
on its first run in 13 of 16 trials in each tier and the bounded repair loop dispatched 18
(Haiku) and 15 (Sonnet) fixes; per-PR trials show 7–8 `Agent` dispatches (control, placebo
and final show 6) and 8–9 driver invocations per trial; the placebo ceremony fired in every
placebo trial; the convoy provenance line is present on 27 of the 32 final-arm rows, and
the five without it are exactly the five trials whose bounded repair loop ended still red
after its two fixes. Implementer model
snapshots: `claude-haiku-4-5-20251001` from every Haiku transcript; the Sonnet transcripts
carry only the undated alias.

**Cost and time** (per trial, mean; from the run rows):

| arm | Haiku $ / s | Sonnet $ / s | $ per held-out-clean trial, Haiku / Sonnet |
|---|---|---|---|
| control | 1.93 / 826 | 2.28 / 669 | 7.72 / 18.24 |
| placebo | 2.11 / 821 | 2.58 / 675 | 5.63 / 8.26 |
| perpr | 2.31 / 974 | 2.85 / 763 | 2.31 / 3.26 |
| final | 2.39 / 1002 | 2.66 / 740 | 3.19 / 4.73 |

The per-PR gate costs 20–25% more per trial than control and 15–20% more wall-clock; per
held-out-clean trial it costs a third (Haiku) to a fifth (Sonnet) of control.

## Conclusion

**Supported, at both implementer tiers.** With a Sonnet orchestrator dispatching one
implementer per PR, running convoy's standalone gate after each PR raised the held-out-clean
rate from 4/16 to 16/16 (Haiku) and from 2/16 to 14/16 (Sonnet). A ceremony gate that
reddens once and carries no information did not (6/16 and 5/16), so the gain is the gate's
independent information — checks the implementer did not write, phase-scoped, with a
repair brief — and not the extra iteration a gate forces. The post-session gate recovers
part of the gap (12/16 and 9/16) at the cost of a repair loop that fires on 13 of 16
trials; it beats control at both tiers and the placebo only at the Haiku tier at this n.
The gate makes each trial dearer and each correct trial much cheaper.

What the result does *not* say: it is one bank, one task family, one orchestrator model,
two implementer tiers, convoy 0.11.0's standalone gate driven by a script the harness
placed in the brief. The v1 pilot showed the whole effect vanishes when the PR prompts
spell out the rule the oracle checks (24/24 at every cell), so the claim is scoped to
briefs that leave the implementer something to infer — which is what a real relay from an
orchestrator to a subagent looks like, and why bank v2 was built that way.

## What happened to the plan (deviations, in order)

1. **The v1 bank was at ceiling** (24/24 across every cell, both tiers): when the PR prompts
   spell out the type rule, there is nothing for a gate to catch. Bank v2 withholds the rule
   from the prompts; its pilot showed headroom at both tiers. (Addendum 2026-09-02, the pilot
   readout.)
2. **n was declared 16 per cell, budget-bound** (exact power 0.69 on the decisive perpr vs
   placebo contrast at Holm's strictest step), run as repeat passes because the run loop's
   order blocks arms.
3. **A fixture-contamination incident** stopped the matrix at 41 trial rows: agents inside two
   trials edited the bank fixture through a path the harness exposed, and thirteen later
   trials staged from the modified fixture. Sixteen trial rows were voided (append-only
   `kind: void` rows carrying the evidence), the fixture restored, the harness repaired (a
   staged harness directory outside the repository, a fixture integrity guard, `fixture_sha`
   on every row), n re-declared 13 within the budget as then computed, and every voided key
   re-bought. (Addendum 2026-09-02 17:10Z.)
4. **The incident addendum's budget arithmetic was wrong** — the v2 pilot's spend had been
   counted twice — and the correction, declared at 48 valid trials, returned n to the frozen
   16. No design amendment was needed; the disposition counts 128 completed trials in the
   frozen cells and the voided rows sit outside the design. (Correction 2026-09-02 22:50Z.)
5. **The last pass overran the iteration cap by about $8**: the bank closed at $352.02 and
   the program at $408.04 against the $400 pre-registered cap; the user authorized the
   overage with three of the pass's eight trials done. (Run log 2026-09-03.)
6. **The typed record was frozen after the run it governs began.** The prose
   pre-registration was committed before each wave — the cells, endpoints, contrasts and
   pilot n at 04:59:50Z (the pilot's first trial: 05:51:34Z), n = 16 and the pass schedule
   at 12:45:49Z (the main matrix's first trial: 12:47:29Z) — but the typed record that
   transcribes it was committed at 13:41:47Z. The gate's chronology check (`ER-ANCHOR`)
   reads the record's commit, fails, and is left failing: the record's `run.attestation`
   discloses the sequence with the commit hashes rather than moving a timestamp. Every
   other gate passes (`ER-PREREG` reconciles the frozen subset against that commit;
   `render.py --check` is clean).

## Threats the record carries (statements in `record.yaml`)

Contamination/familiarity (residual), prompt-format sensitivity (controlled), judge bias
(controlled: deterministic verifier, disjoint from every gate assertion), model version
drift (residual: Sonnet snapshots undated), nondeterminism (controlled), construct validity
(residual: one task shape), token-length confound (residual: the placebo is the
length/iteration control, and it did not move the rate), selection and exclusion
(**residual**: an instrument exclusion the plan did not foresee, defined on timestamp and
stream facts, blind to outcome, declared before any resumed trial), generalization
(residual).

## What this updates

- **Convoy's gate as a feature under external orchestration** (convoy backlog CONV-B53):
  from "measured in iteration 1, in flight" to supported at measurement tier on one bank.
  The mechanism that worked is the per-PR standalone gate with phase-scoped independent
  checks and a repair brief; the post-session gate is the weaker form.
- **The mechanism to measure next** is convoy 0.12.0's hook (`convoy hook`: `SubagentStop`
  as the judge, `PostToolUse` on `Agent` as the messenger), which reaches the same gate with
  no orchestrator instruction at all. Its two arms (`hook-haiku`, `hook-sonnet`) are
  pre-registered on this bank with control's brief plus one phase-marker instruction and
  the prediction `held_out_clean` ≈ perpr at control's orchestrator turns and tokens; they
  run at the start of iteration 2 under its own cap.
- **Generalization** is the open question the next bank must answer: a hard bank drawn from
  real merges (treasuryutils), tiers crossed with oracles, per the program-2 design.
