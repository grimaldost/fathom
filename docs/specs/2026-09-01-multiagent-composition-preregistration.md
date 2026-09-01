# Pre-registration — multiagent dispatch + convoy's features vs multiagent dispatch alone

- **Date:** 2026-09-01. **Status:** pre-registered for the PILOT stage; the main-matrix
  stage is pre-registered in an addendum to this file after the pilot reads out, before
  its first paid trial. Nothing below changes after data exists except by a dated
  addendum that says what changed and why.
- **Audience:** the operator approving spend; a blind reviewer checking the report
  against what was declared here.
- **Predecessor:** `2026-09-01-convoy-gate-composition-design.md` and the retractions in
  `docs/reports/2026-09-01-gate-composition-findings.md`. Every defect that review found is
  a design constraint here, named where it bites.

## The stance (binding on the operator)

The operator wants convoy to win. The licensed route is improving convoy. Forbidden: arm
asymmetries that favor convoy, post-hoc metric or contrast choice, unregistered tests,
any claim a blind reviewer would strike. A loss is a finding and is published as one. A
convoy change made to win ships through convoy's repo process, is tagged, and is measured
as a **new arm** — never a mutation of a running one.

## Question

Does a Claude session dispatching one implementer subagent per PR produce better
held-out-verified work when, between PRs, it uses **convoy's standalone gate** (fail-closed
independent checks, structured repair briefs, phase-scoped checks) than when it verifies
with the project's own suite alone — and is any gain the *independent information*, not
the extra iteration?

Convoy's orchestration (`convoy run`) appears in **no** arm.

## Bank: `multiagent-composition` (new — the old bank is not mutated)

`tasks/multiagent-composition/exprlang/`: a copy of `ablation-v2/exprlang`'s fixtures,
reference solution, the 5-PR decomposition (`series.toml` + `prompts/`), plus:

- **`verify.py` extended with a `held_out` group** — six criteria the gate's checks never
  assert, targeting classes weak implementers get wrong:
  `type_bool_arith_heldout` (`"false * 3"`, `"7 - false"`, `"true % 2"`, `"-(1 < 2)"`,
  `"(true) + (false)"` → all errors), `type_compare_heldout` (`"false > true"`,
  `"2 != true"`, `"(1 < 2) < 3"`, `"true <= true"` → errors), `env_bool_typing` (env
  `{p: True, q: False}`: `"p and true"` → True, `"p + 1"` → error, `"not p"` → False,
  `"p == q"` → error), `not_precedence_heldout` (`"not 1 + 1 < 3"` → False,
  `"not true and false"` → False, `"not not true"` → True), `error_type_is_typemismatch`
  (the raised class is named `TypeMismatchError` and subclasses `ExprError`),
  `short_circuit_heldout` (`"(1 > 2) and (1 / 0 == 1)"` → False, `"(1 < 2) or (1 / 0 == 1)"`
  → True). The original 15 criteria are kept as the `full` group.
- **`type_probe.py` de-overlapped**: `"true * 3"`, `"5 - false"`, `"-false"`, `"false / 4"`,
  `"true % 5"`, `"3 + true"`, `"2 == true"`, `"false < 1"`, `"true >= false"`, `"1 > false"`.
  A test asserts `probe_cases ∩ (full ∪ held_out) = ∅` as literal strings, and that no
  probe case is a whitespace/parenthesis variant of a graded item.
- **`placebo_gate.py <workspace>`**: exits 1 on its first invocation per workspace
  (marker under the OS temp dir keyed by workspace path hash) with the uninformative text
  "quality gate: a transient check failed — re-run your verification and fix any issue",
  exits 0 thereafter. Same ceremony as a gate, zero information.
- **`run_convoy_gate.py`** (the arming-verified driver, UTF-8-hardened) gains `--phase`
  passthrough and emits the JSON envelope on stdout. The materialized gate spec reuses
  `series.toml`'s own `[[checks]]` (authored for per-PR gating of this decomposition) plus
  two blocking `independent = true` checks with out-of-tree `asset`: the arithmetic probe
  scoped to phases `bools..conform`, the comparison probe scoped to `compare..conform`, each
  with a `repair_hint` stating the type rule.
- `bank.toml`: `dataset_version = "1"`, ledger `ledger/multiagent-composition.jsonl`.

**Bank validity gates before spend:** verifier passes on `solution/` with `held_out` all
true; a reference **escape** implementation (solution minus `and not isinstance(v, bool)`)
passes the visible suite 20/20, fails `type_bool_arith_heldout`, and the de-overlapped
probe goes red on it; the placebo reddens exactly once per fresh workspace; `fathom
validate` clean.

## Arms — 4 treatments × 2 implementer tier-sets, orchestrator fixed

Every arm is a spawned Claude session (**orchestrator, Sonnet 5, effort high**) that
dispatches one implementer subagent per PR via the `Task` tool, in dependency order,
integrates, and finishes. Tool allow-list, limits, `[env]` keys, and orchestrator model
are **byte-identical across arms**; the arms differ in the injected brief only, and
T-final additionally in a harness gate. Implementer model is the `[env]` value
`FATHOM_IMPL_MODEL`, identical across arms within a tier-set.

| Arm | Brief tells the orchestrator, after each PR… | Reads as |
|---|---|---|
| **C** control | verify with the project's visible suite; fix if red; move on | multiagent alone |
| **P** placebo | C + run `python $FATHOM_PLACEBO_GATE .`; if it fails, re-verify and fix | the extra iteration without independent information |
| **T-perPR** | C + run `python $CONVOY_GATE_DRIVER $FATHOM_TASK_DIR . --phase <pr phase> --json`; if `outcome` is `blocked`, dispatch a fix subagent with the envelope's `repair_brief` verbatim; re-run until `completed` | convoy's features, agent-driven |
| **T-final** | C's brief unchanged; the **harness** runs the driver once after the session (`gated-session`, `[gate].extra`) with a bounded fix loop | convoy's features, harness-driven |

Tier-sets: **haiku** (`FATHOM_IMPL_MODEL=claude-haiku-4-5` — the regime with measured
headroom) and **sonnet** (`claude-sonnet-5` — what the choosing-models rubric assigns to
all five PRs, scores 46–53, and the tier the operator actually dispatches; the corpus
predicts saturation here, which is itself a pre-registered prediction).

Pre-registered predictions: on haiku, T-perPR > P > C on the primary endpoint, with
T-perPR − P > 0 (the independent-information effect); on sonnet, all arms near ceiling.
If T-perPR ≈ P on haiku, the gate's value is the iteration, not the information.

## Endpoints, tests, decisions

- **Primary endpoint:** `held_out_clean` — a trial passes iff all six `held_out` criteria
  are true. Chosen because the gate cannot assert it.
- **Secondary:** `full_clean` (all 15 original criteria); first-gate red rate and fix-round
  count (mechanism, T arms only); `convoy gate` invocation count per trial from persisted
  transcripts (attestation, T-perPR); cost per **trial** (sum of run rows sharing
  `(config_hash, repeat)`) and wall-clock.
- **Contrasts, one-sided (treatment > control), Holm-corrected within the family,
  α = 0.05, per tier-set:** (1) T-perPR vs C; (2) **T-perPR vs P** — the decisive one;
  (3) T-final vs C; (4) T-final vs P. Fisher exact on `held_out_clean` counts. Wilson 95%
  intervals reported for every cell. No other contrast is tested; any exploratory
  reading is labeled exploratory.
- **Pilot (this stage):** n = 3 per cell, 8 cells, 24 trials. Purpose: arming
  (every T-perPR transcript must show ≥ 1 driver invocation; T-final ledger `detail`
  must carry a gate verdict; placebo must fire in every P trial), rate estimation, cost
  estimation. **No inference is drawn from the pilot.**
- **Main matrix (addendum after pilot):** n per cell from a power calculation at 0.8 on
  the pilot's observed T-perPR − P gap on haiku, bounded by the remaining budget; if the
  pilot shows sonnet at ceiling on all arms, the sonnet tier-set is dropped from the main
  matrix and that is reported as the tier finding. Trials **interleaved across arms and
  tier-sets** (the run loop's default round-robin is verified before the run), all cells
  bought in one batch.
- **Stopping rule:** the matrix runs to its declared n; no peeking-based stop.
- **Budget:** $400 per iteration, pilot included. Dry-run and a ledger-derived estimate
  precede every run.

## Attestation and hygiene (each is a defect from the previous round)

- `FATHOM_STREAM_DIR` is set for every run; transcripts are the record of what the agent
  invoked. A T-perPR trial with zero driver invocations is scored but flagged, and the
  arm's adoption rate is reported.
- The driver echoes `convoy gate via: <pin>` on every call; the harness-side arm's gate
  output lands in `detail`. The envelope carries `convoy_version`.
- Arm versioning: any edit to the driver, probes, placebo, `verify.py` or a brief bumps the
  affected arm names (config preimage does not hash referenced files).
- Cost is reported per trial, never per spawn. Tier-sets are not pooled.
- The report is blind-reviewed before any claim leaves the repo.

## Convoy changes shipped for this iteration (measured as part of the T arms)

Derived from evidence, not from the wish to win: (1) the gate envelope gains
`repair_brief` — the run's own fix-brief fold, so an orchestrator hands a red to a fix
subagent verbatim; (2) the envelope gains `convoy_version` (attestation); (3) `convoy
validate` accepts gate-only files; (4) the authoring doctrine states that adopting the gate
surface without an implementer-unreachable check leaves you where you started (supported
by the within-arm observation, not by the voided A4). All ship as convoy 0.11.0 before the
pilot; the driver pins that tag.

## Non-goals

No strong-tier arms this iteration; no new task bank; no `haiku-series` (convoy's runner
is out of scope by the question's definition); no claim about tasks other than this one.
