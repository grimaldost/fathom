# ADR-0007 — Model-tier calibration study design

- **Status:** Accepted
- **Date:** 2026-06-16

## Context

The series engine's `model-tiers` skill routes a task by a complexity score: 0-25 → Haiku
(weak), 26-55 → Sonnet (mid), 56-100 → Opus (strong). Every series the engine runs depends
on this mapping, but the skill itself records *no observed-run calibration* — the
thresholds are reasoned, not measured. The `model-tier-v1` study tests whether the
mapping is well-tuned, on this operator's task distribution, using fathom's blind
verifier + economy join. The harness already carries `model` and `effort` as hashed
scenario fields, so an arm is a `(model, effort)` pair with no spawn-path code change.

This ADR records the load-bearing design decisions and their rejected alternatives.
The full spec is `docs/specs/2026-06-16-fathom-model-tier-calibration-design.md`,
certified through keel DoR (pre-mortem rounds 1-4).

## Decisions

### D1 — Two-knob framing (model = capacity, effort = thinking)

The mapping manages only *model*. Effort (`--effort low|medium|high|xhigh|max`) is a
separate test-time-compute dimension. We measure model as the main factor and stage
effort (D5).
*Rejected:* treating "compute" as one axis — it conflates two independently-routable
knobs and would hide the substitution question (can a cheaper model at higher effort
match a dearer one?).

### D2 — Quality metric = verifier fraction over **designated HARD criteria**

Each task declares ≥2 HARD (capability-gated) criteria. The calibration scalar is
`quality(task, arm) = (# true HARD criteria) / (# HARD criteria)` ∈ [0,1]. The full
criteria set still feeds the per-criterion table and the dose-response, but the
calibration scalar is hard-criteria-only so one genuine capability failure is never
diluted below ε by many easy criteria.
*Rejected:* (a) the all-truthy AND that `verifier.py` exit-code and `report.py`
`_is_pass` use — it collapses the gradient to pass/fail and ceilings; (b) the mean
fraction over *all* criteria — count-sensitive, an authoring nuisance parameter could
move the headline confusion matrix; (c) the ordinal judge — it has no cardinal scale
for ε (see D6).

### D3 — "Right tier" = cheapest model within ε of the best, with a pooled-CI overlap guard

For a task, the empirically-right tier is the cheapest model whose mean HARD-criteria
quality fraction is within **ε = 0.10** (fraction units) of the best model's, AND
whose Wilson CI overlaps it. The CI is computed on criteria **pooled across the
task's trials** for a model: `successes = Σ true HARD criteria`, `n = Σ total HARD
criteria` → `wilson_interval(successes, n)` (the per-trial mean fraction is the point
estimate; the pooled proportion is the integer-count basis the existing helper needs).
A raw mean of per-trial fractions has no integer count and thus no Wilson CI. The
pooled proportion treats correlated criteria as independent, so the CI is a heuristic
width, not an exact coverage guarantee. A tier whose ε-decision rests on overlapping
CIs is labeled **indeterminate**, never forced onto the diagonal.
*Rejected:* a bare point estimate with no CI — at n≈5 repeats it would force noisy
borderline tasks into confident "well-tuned"/"mis-provisioned" cells.

### D4 — Continuous difficulty ladder (not discrete buckets)

Tasks are spread across the 0-100 score range and analyzed as a quality-vs-complexity
curve per model, so the *boundary placement* at 25 and 55 is testable (the crossover
score where the empirically-right model steps up, compared to 25/55), not merely tier
ordering. Because the scorer rubric scores *prompt* complexity, not *model* difficulty
(the v3 pilot ceilinged even Opus on high-scored self-contained functions), each
high-band task must name the concrete capability the weak model (Haiku) is expected to
*lack*, and an independent second rater + a spread gate force boundary rungs to exist.
*Rejected:* three lumpy bands — they can confirm ordering but cannot locate a mis-set
boundary.

### D5 — Effort staged, not crossed

The main matrix fixes `effort=high`; an effort layer (substitution cells, capped at
`xhigh`) is added only if a pilot shows effort moves quality on the mid/high bands.
*Rejected:* a full 4-model × 5-effort factorial — a 5× blowup of mostly-dominated
cells with worse token-TTL exposure.

### D6 — Judge as a validated, ordinal, secondary corroboration

The dark pairwise judge is lit as net-new all-pairs plumbing + a non-bare aggregation,
validated (gold-set agreement + position-consistency) before any verdict cites it. It
is ordinal (win/tie/loss), does NOT define ε or the confusion matrix, and is
deferrable: the calibration verdict rests on the verifier fraction (D2), so a failed
validation or a descope falls back to verifier-only with the judge axis marked
untrusted.
*Rejected:* making the judge the primary quality axis — an ordinal signal can't carry
ε, and trusting it unvalidated repeats the position-bias trap.

### D7 — Cost axis is a token×price estimate

Subscription auth reports `total_cost_usd = 0` (D2 in STATUS), so the cost/Pareto axis
is the token×price estimate using the pinned `model-tiers` per-1k rates, named as such
so the crossover is not read as billed dollars.
*Rejected:* reporting `$0` from the CLI — it would make every arm look free.

## Consequences

- The confusion matrix (predicted tier vs empirically-right tier) is the headline; the
  per-band dose-response and the (model×effort) Pareto frontier are the economy views;
  the crossover-vs-threshold line is the boundary-placement test.
- Results at ~5 repeats/cell are directional (Wilson half-widths are wide); the report
  labels indeterminate cells rather than over-claiming, and the recommendation to
  `model-tiers` is stated with that caveat.
- The bank, scenarios, and report views are stdlib-only and blind (ADR-0003);
  `model`/`effort` already enter `config_hash` (ADR-0002), so the ledger forks
  correctly and resumes soundly.
