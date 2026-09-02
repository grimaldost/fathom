# Findings — multiagent dispatch with convoy's gate versus multiagent dispatch alone (iteration 1)

[experiment-rigor | measurement -> experiments/multiagent-composition-v2/record.yaml]

**Status: DRAFT — the main matrix is in flight; every number below is a placeholder until
`record.yaml` is filled and `report.md` is derived. The derived report is the source of
numbers; this document explains, points, and records what the numbers cannot say.**

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
probe. Four pre-registered one-sided contrasts per tier-set, Holm-corrected within the
tier-set; Wilson 95% intervals on every cell; tier-sets never pooled. Pre-registration:
`docs/specs/2026-09-01-multiagent-composition-preregistration.md` and its dated addenda;
frozen record: `experiments/multiagent-composition-v2/record.yaml`.

## What happened to the plan (deviations, in order)

1. **The v1 bank was at ceiling** (24/24 across every cell, both tiers): when the PR prompts
   spell out the type rule, there is nothing for a gate to catch. Bank v2 withholds the rule
   from the prompts; the pilot showed headroom at both tiers. (Addendum 2026-09-02, the pilot
   readout.)
2. **n was declared 16 per cell, budget-bound** (exact power 0.69 on the decisive perpr vs
   placebo contrast), run as repeat passes because the run loop's order blocks arms.
3. **A fixture-contamination incident** stopped the matrix at 41 trial rows: two trials'
   agents edited the bank fixture through a path the harness exposed, and thirteen later
   trials staged from the modified fixture. Sixteen trial rows were voided (append-only
   `kind: void` rows with the evidence), the fixture restored, the harness repaired (a staged
   harness directory outside the repository, a fixture integrity guard, `fixture_sha` on
   every row), and **n re-declared 13 per cell** within the iteration's budget, with exact
   power 0.532 on the decisive contrast. (Addendum 2026-09-02 17:10Z; `design.amendments[]`
   in the record.)
4. **The typed record was frozen after the run it governs began**: the prose
   pre-registration of the main matrix was committed before its first trial, the typed
   record 55 minutes after it and eight hours after the pooled pilot. The gate's chronology
   check reads the record's commit; the report says so rather than moving a timestamp.

## Results

_To be derived from `report.md` when the matrix closes: per-cell numerator/denominator and
Wilson interval; the four contrasts per tier-set with one-sided Fisher p and Holm-adjusted
p; the sensitivity endpoint; cost per trial and per correct trial; first-gate red rate and
fix dispatches per arm from the ledger detail and the streams._

Interim, on the 25 valid trials at the incident (no inference; the same numbers the
resumed matrix subsumes): control 0/4 and 0/4, placebo 1/3 and 1/3, perpr 2/2 and 3/3,
final 3/3 and 2/3 on `held_out_clean` (Haiku then Sonnet tier-set).

## The mechanism this iteration built, measured in Part 2

Convoy 0.12.0 ships the gate as a Claude Code hook (`convoy hook`): `SubagentStop` is the
judge — a blocking red is handed to the subagent as the reason it may not stop yet, one
repair round — and `PostToolUse` on `Agent` is the messenger for synchronous dispatch. The
per-project spec (`.convoy/gate.toml`, `convoy gate --init`, `--trust`) and the harness-side
spec (`$CONVOY_GATE_SPEC`, `CONVOY_TRUSTED_ROOTS`) make the gate reachable with no
orchestrator instruction at all. Two hook arms (`hook-haiku`, `hook-sonnet`) are
pre-registered on this bank with control's brief plus one phase-marker instruction; their
prediction is `held_out_clean` ≈ perpr at control's orchestrator turns and tokens.

## Threats the record carries (see `record.yaml` for the statement of each)

contamination/familiarity (residual), prompt-format sensitivity (controlled), judge bias
(controlled: deterministic verifier, disjoint from every gate assertion), model version
drift (residual), nondeterminism (controlled), construct validity (residual: one task shape),
token-length confound (residual: placebo is the length/iteration control), selection and
exclusion (**residual after the incident**: an instrument exclusion defined by timestamp and
stream facts, declared before any resumed trial), generalization (residual).

## What this updates

_To be written with the numbers._
