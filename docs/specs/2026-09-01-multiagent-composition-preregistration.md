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

## Addendum — 2026-09-01, before the pilot's first paid trial

Cause: a blind review of the built bank and the eight arms. No trial has run and no
money has been spent. Nothing below edits a brief, the driver, the probes, the placebo
or `verify.py`, so no `config_hash` moves and no arm is renamed.

**1. Run preconditions, now written down.** The two exports the attestation depends on
(`FATHOM_TASK_DIR`, `FATHOM_STREAM_DIR`), the requirement that convoy 0.11.0 be tagged
and its echo observed **without** the local override before the matrix starts, and the
uv cache warm-up, are stated as a checklist in
`scenarios/multiagent-composition/README.md`. The `perpr-*` invocation count and adoption
rate are derivable only from the transcripts, and only if `FATHOM_STREAM_DIR` was set:
a forgotten export is unrecoverable after the spend, not a nuisance.

**2. A cold gate install must not read as a defect.** `gated-session` kills a gate command
at `_GATE_TIMEOUT_S` = 120s and scores the timeout as a red, which on a `final-*` trial
buys fix spawns for a defect that does not exist. The operator times one warm
`run_convoy_gate.py` call before the matrix; if it is not comfortably inside the timeout,
raising `_GATE_TIMEOUT_S` for this run is pre-approved and is recorded in the run log. It
is harness config, not an arm field.

**3. T-final's gate output lands in `detail`, and that is what makes the attestation
sayable.** The `gated-session` executor now records the extra gate's own output — bounded,
whitespace-condensed, first round and final round — beside the `first=/final=` verdict, so
a `final-*` row says which convoy ran and what it reported, and distinguishes a
visible-suite red (which short-circuits before convoy runs) from a convoy red. This is a
harness change shipped through the repo's own process, not an arm change. Absent it, no
T-final convoy-provenance claim is made.

**4. A pre-registered sensitivity on the primary endpoint.** Two of the six `held_out`
criteria are rule-adjacent to the treatment: the probes' `repair_hint` states the type rule
(including that `bool` subclasses `int`, which appears nowhere in the task statement or the
PR prompts), and the probe cases exercise the same rule as `type_bool_arith_heldout` and
`type_compare_heldout` with different literals. The primary endpoint stays
`held_out_clean`. Alongside it, and with the same contrasts, the same one-sided tests and
the same Wilson intervals, the report also states
`held_out_clean_independent` — the conjunction of the four criteria the hint and the probes
do not touch: `env_bool_typing`, `not_precedence_heldout`, `error_type_is_typemismatch`,
`short_circuit_heldout`. It is a sensitivity analysis, declared here before any data
exists; it does not replace the primary and does not enter the Holm family. If the two
disagree in direction, the report says so and leads with the disagreement.

**5. Contrast (2) is reported with its dose.** T-perPR can go red on any of five phases and
dispatches a fresh fix subagent each time; P reds exactly once per trial and fixes in the
orchestrator itself. Both are faithful to the arm definitions above, but the pair is not
iteration-matched, so per arm and per trial the report states the observed number of gate
reds and the number of fix dispatches. If those counts diverge materially, T-perPR vs P is
reported as dose-confounded rather than as the independent-information effect.

**6. Two wording defects, deferred to the next arm-version bump** — editing either file now
would fork the T arms for no measurement gain, and both carry no task content. The driver's
docstring says each `repair_hint` states the rule "in the task statement's own words"; it
does not. `brief-treatment-perpr.md` says "The gate's checks are the project's own"; six of
the eight are, and the two type-contract probes are harness-authored.

**7. The hint leak is removed, not carried (supersedes the "deferred" half of #6).** Before
any trial: the two `repair_hint` strings restated the type rule *and* added "bool is a
subclass of int in Python, so excluding it takes an explicit check" — an implementation
tip that appears nowhere in the task statement or the PR prompts, so the treatment arms
would have been told something the control arm could not know. That is an arm asymmetry in
convoy's favor and the persona forbids it regardless of size. The hints now quote task rule
4 and nothing else; the brief's "the project's own" wording and the driver docstring are
corrected in the same commit. No ledger row exists under any of the eight hashes, so no arm
is renamed. The `held_out_clean_independent` sensitivity endpoint (#4) is kept: the probes
still exercise the same rule as two held-out criteria with different literals.

## Addendum — 2026-09-02, the pilot readout and the decision it forces

**Pilot as run.** 24/24 trials completed, $56.02 est. (ledger `multiagent-composition`,
readout by `tools/readout_multiagent.py`, transcripts in `streams-multiagent/2026-09-01-pilot`).
Per the pre-registration, no inference is drawn from it. The numbers, for the record:

| cell | held_out_clean | ho_independent | full15 | $/trial (median) | wall s (median) |
|---|---|---|---|---|---|
| control-haiku | 3/3 | 3/3 | 3/3 | 2.03 | 645 |
| placebo-haiku | 3/3 | 3/3 | 3/3 | 2.15 | 992 |
| perpr-haiku | 3/3 | 3/3 | 3/3 | 2.17 | 908 |
| final-haiku | 3/3 | 3/3 | 3/3 | 1.81 | 784 |
| control-sonnet | 3/3 | 3/3 | 3/3 | 2.41 | 645 |
| placebo-sonnet | 3/3 | 3/3 | 3/3 | 2.64 | 653 |
| perpr-sonnet | 3/3 | 3/3 | 3/3 | 2.80 | 792 |
| final-sonnet | 3/3 | 3/3 | 3/3 | 2.43 | 684 |

Every pre-registered contrast is 3/3 vs 3/3 (one-sided p = 1.0; Holm 1.0). The `final-*`
harness gate went red in 0 of 6 trials.

**Arming criteria — all met, with two notes.** Every `perpr-*` transcript shows the driver
invoked (7–16 times per trial); every `placebo-*` transcript shows the placebo fired; all
six `final-*` rows carry the convoy provenance line in `detail`. Mechanism attestation the
pre-registration did not list but the transcripts give: 5–6 `Agent` dispatches per trial
in every arm (two placebo trials show 5 — one dispatch fewer than PRs; the readout counts
tool-use events, and a single dispatch may have covered two PRs or one may have failed
and been retried in-orchestrator; the implementations still passed every criterion), the
subagents requested at the pinned tier, orchestrator at Sonnet, and — a bonus the ledger
lacks — the haiku subagents' **dated** snapshot `claude-haiku-4-5-20251001`. Sonnet events
carry only the undated alias; that tier-set's snapshot remains unpinnable.

**Two hygiene findings, disclosed.** (1) Arms ran as **blocks** (all repeats of one arm,
then the next), not interleaved as promised: the run loop is scenario → task → repeat and
I did not verify it before launching. Time drift is confounded with arm across a
~2.5-hour window. Tolerable for a pilot that infers nothing; the main matrix runs as
repeat passes (`--repeats k` for k = 1..n, each pass covering every arm once — verified to
resume correctly mid-pilot). (2) Two non-treatment orchestrators (`final-sonnet` r0,
`placebo-sonnet` r2) saw the driver's filename — via a directory listing of the task dir
and via `series.toml`'s header comment, both readable because the brief points the
orchestrator at that directory for the prompts. Neither **executed** it (no Bash tool-use
carries it in either transcript). Not contamination; a leak of the arm structure that v2
removes.

**The decision, per the ceiling rule committed at trial 6 of 24 (before any treatment
trial landed):** the control cell is 3/3 in **both** tier-sets, so this bank has no
headroom on the primary endpoint at either tier. **No main matrix is bought on this bank
version.** The round's finding, stated at the strength n=3 allows: *a five-PR decomposition
whose prompts spell out the type-rule matrix per PR produces held-out-clean work from
multiagent dispatch alone, at the weak tier as at the mid tier; the gate had nothing to
catch, and the placebo ceremony and the per-PR gate loop cost wall-clock (+54% and +41%
at haiku, +1% and +23% at sonnet) for no measurable quality.* The suspected cause is the
prompts: they were authored as briefs for convoy's own runner, with the oracle written
into them (PR01: "Arithmetic rejects booleans … raises `TypeMismatchError` … use the
numeric guard"; PR05 restates the whole matrix as a conformance pass). Against a brief
that explicit, even a weak implementer has nothing left to infer.

## Pre-registration — bank v2 (`multiagent-composition-v2`), before its first paid trial

**Hypothesis the v1 ceiling licenses:** the value of an independent gate under external
orchestration scales with how much the implementer is left to infer. v2 makes the relay
from orchestrator to subagent realistic and lossy: the task statement (which the
orchestrator holds) keeps every rule; the per-PR prompts describe the behavior to build
and stop restating the type-rule matrix and the guard recipe.

**Bank v2 = v1 with exactly these changes**, so the primary endpoint, probes, placebo,
driver, verify.py and arms stay byte-identical to v1:

- `prompts/01..04`: remove the sentences that state the type rule or prescribe the guard
  (PR01 items 3 and the guard bullet; PR02–04's "an operand of the wrong type raises
  `TypeMismatchError` — use PR01's … guard" clauses and the "PR01 already landed: … the
  arithmetic operators reject boolean operands, and the evaluator carries a numeric-operand
  guard and a boolean-operand guard" recaps). Each PR keeps: what to add, the AST shape,
  precedence placement, the test targets to run. PR01 keeps "add `TypeMismatchError` as a
  new subclass of `ExprError`" (it is an artifact the later PRs import), but not what
  raises it.
- `prompts/05`: the conformance pass keeps "run the whole suite and close what is red";
  the type-rule matrix restatement (its items 32–37 in v1) is removed.
- A test asserts, for each v2 prompt, the absence of the removed phrases (`reject`,
  `wrong type`, `numeric-operand guard`, `boolean-operand guard`, `require NUMERIC`,
  `require BOOLEAN`), and that `task.toml`'s instruction is byte-identical to v1's.
- Prompts move to `prompts/` under a directory the brief names as `$FATHOM_PROMPTS_DIR`
  that contains **only** the five prompt files; the driver, probe, placebo and
  `series.toml` stay in the task dir, which the briefs never name. `[env]` keys stay
  identical across arms.
- Scenarios: `scenarios/multiagent-composition-v2/`, same eight arms, same briefs except
  the prompts-dir variable, new bank name ⇒ new `config_hash`es. Ledger
  `ledger/multiagent-composition-v2.jsonl`.

**Endpoints, contrasts, tests, corrections, attestation: unchanged from the v1
pre-registration.** Tier-sets: both, at the pilot; the ceiling rule (control ≥ 2/3 in a
tier-set ⇒ that tier-set not bought at scale) applies again. Pilot n = 3 per cell (24
trials, ≤ $100). Main matrix: pre-registered in a further addendum from the v2 pilot's
observed perpr − placebo gap on the tier-set with headroom, run as repeat passes, within
the iteration's remaining budget ($400 − $56 pilot v1 − v2 pilot).

**Prediction, pre-registered:** control-haiku held_out_clean falls below ceiling on v2;
control-sonnet may not. If control-haiku stays at 3/3 on v2, the decomposition itself,
not the prompts' explicitness, is what removes the defect class, and that is reported as
the finding of the iteration.

*Run log, 2026-09-02 ~00:10 — the v2 pilot stopped at 7 of 24 trials by the harness on
`authentication_failed` (the seat's refresh failed again ~4 h after login; $14.81 spent; the
seven completed trials are in the ledger, the failing eighth was not written). Recorded
here as a log line, drawing nothing: control-haiku 0/3, control-sonnet 0/3 on
`held_out_clean` (and 0/3 on the original 15); the single completed `final-haiku` trial
went first-gate red, repaired once, and reads 1/1 on every endpoint. The pilot resumes with
the same command once the seat is re-authenticated; the readout and the ceiling rule apply
to the completed 24, not to this fragment.*

## Addendum — 2026-09-02, the v2 pilot readout and the main-matrix pre-registration

**v2 pilot as run:** 24/24 completed, $57.46. `held_out_clean` — control 0/3 (haiku) and
0/3 (sonnet); placebo 1/3 and 1/3; per-PR convoy gate 3/3 and 3/3; final convoy gate 3/3
and 2/3. The sensitivity endpoint and the original 15 read identically. Every `final-*`
first harness gate went red (6/6; 5 repaired). Arming criteria met in every trial
(`perpr-*` driver invocations 8–19, placebo fired 6/6, provenance 6/6). No inference is
drawn from these 24; they are the pilot the pre-registration describes.

**The ceiling rule:** control is 0/3 in both tier-sets — headroom in both. Neither tier-set
is dropped; the v1 prediction that Sonnet might stay at ceiling was wrong, and that is
recorded as the v1→v2 finding: the prompts' explicitness, not the tier, produced the v1
ceiling.

**Main matrix, pre-registered before its first trial:**

- **n.** The pre-registered calculation (exact one-sided Fisher, α = 0.0125 = Holm's
  strictest step over the four contrasts, Laplace-shrunk pilot rates 0.875 vs 0.375 for
  T-perPR vs P) asks **n = 20 per cell for power 0.80**. The remaining budget ($400 −
  $56.02 − $57.46 = $286.52) buys 13 further repeat passes over eight arms at the pilot's
  observed $19.15 per pass with a 10% margin. **n = 16 per cell** (3 pilot + 13 main) is
  therefore the budget-bound n; its exact power on the decisive contrast is **0.69** per
  tier-set, and 0.99 on T-perPR vs C. Declared now: a non-significant decisive contrast at
  n = 16 is reported as *underpowered at the achieved n*, not as a null.
- **Pooling.** The pilot's 3 repeats per arm are the first three of the 16 — same arms,
  same `config_hash`es, contemporaneous, resumed by the run loop as already done. They
  were block-ordered (disclosed above); passes 4–16 are arm-interleaved by pass.
- **Order.** `--repeats k` for k = 4..16, each pass covering every arm once; the loop's
  within-pass order is fixed (alphabetical by arm), so drift is bounded to one pass
  (~25 min) rather than the matrix.
- **Caps.** `--max-spawn-usd 20`, `--max-run-usd 275`. Seat death stops the pass script;
  the same command resumes.
- **Endpoints, contrasts, tests, corrections, attestation: unchanged.** The report leads
  with T-perPR vs P per tier-set (Holm over four), then T-perPR vs C, T-final vs C,
  T-final vs P; the sensitivity endpoint beside each; Wilson intervals on every cell;
  dose counts (gate reds, fix dispatches) per arm; cost and wall-clock per trial. Any
  other reading is exploratory and labeled.
- **Blind review before any claim leaves the repo.**

## Addendum, 2026-09-02 — bank v2 as executed, before its first paid trial

Written after the bank was built and blind-reviewed, before any v2 spend. It records where
the artifact is a superset of, or narrower than, the section above. Nothing here changes a
hypothesis, an endpoint, a contrast or a test; it makes the record match the files.

**Six removals beyond the enumerated list.** Each is a pointer to, or a paraphrase of,
content the section above orders removed, and each moves in the direction of less
information — none restores a rule, and leaving any in would have left a prompt referencing
a section it no longer has:

- PR01's title tail `, and what the existing operators do with them`.
- PR01's paragraph beginning "Because introducing a new value type changes what every
  operator that already exists must do…", which announced that this PR settles the
  arithmetic-meets-boolean question.
- PR02's `requires TWO NUMERIC (int or float) operands` — the clause the held-out criterion
  `type_compare_heldout` grades. The enumerated list named only the adjacent "wrong type …
  use PR01's guard" clause; leaving this one would have stated the operand type for
  comparisons while the mandated absences forced it out of PR03 and PR04, an asymmetry
  nothing was pre-registered to create.
- The `and reuse the guards — do not write a second copy of either` clause in PR02–04.
- PR05's title tail ` and the type-rule matrix`.
- PR05's intro, rewritten from "Two requirements … this PR owns both" to "One requirement …
  this PR owns it", the numbering of its surviving section shifted accordingly.

**One addition.** PR01 item 3 keeps its no-regression sentence (arithmetic on numbers must
not change) under the new label `**Existing arithmetic is unchanged.**`. That label is the
only prose written into any v2 prompt that is not v1's. It states nothing about booleans.

**The type rule is not wholly absent from the prompts, and the readout must not say it is.**
PR03 and PR04 still name the judged check
`tests.test_feature.TestFeature.test_type_error_number_in_boolean_op`, whose name states
that a number in a boolean operation is a type error. Keeping each PR's test targets is
pre-registered, and the visible suite enforces that direction in every arm, so this is
compliant — but it means v2's manipulation is specifically the **bool-in-arithmetic** and
**bool-in-comparison** directions. That is what the primary endpoint grades: all six
`_HELD_OUT` criteria cover bool-in-arithmetic, bool-in-comparison, booleans via `env`,
`not` precedence, and the error class. None grades numbers-in-boolean-ops, so the headroom
the manipulation is meant to create is intact.

**"The task dir, which the briefs never name" is true of three briefs, not four.**
`brief-treatment-perpr.md` still passes `$FATHOM_TASK_DIR` to the gate driver, because
`run_convoy_gate.py` is byte-identical to v1's and takes the task dir as `argv[1]`. The
asymmetry is structurally forced. What confines every arm is instead the do-not-read
sentence, which v1 carried and v2 keeps in all three briefs, re-anchored to
`FATHOM_PROMPTS_DIR` so it names no task-dir path: the prompts dir is a *child* of the task
dir, and `Read`/`Glob`/`Grep` are unrestricted by path in every arm's tool allow-list, so
moving the prompts is not by itself a fence.

**Mechanism correction.** "New bank name ⇒ new `config_hash`es" is wrong as stated. The
bank name does not enter the hashable (`src/fathom/scenario.py`; its `name` is the arm
name). The hashes do fork, because the injected brief content and the `[env]` key set both
changed; ledger separation is real and comes from the per-bank ledger path. The conclusion
stands — no v2 row can resume or overwrite a v1 row — but the derivation was not checked.

## Addendum, 2026-09-02 17:10Z — fixture contamination incident, exclusions, harness repair, and the resumed plan

**Written after the event, before any further paid trial.** This addendum records a defect in
the instrument, not in the arms, and the deviation it forces from the main-matrix
pre-registration above (n = 16 per cell; no exclusion rule).

### What happened

During the main matrix the bank's *fixture* — the committed starting tree every trial stages
its workspace from (`tasks/multiagent-composition-v2/exprlang/fixtures/`) — was modified by
agents inside trials. `git status` at 16:55Z showed four modified files
(`fixtures/exprlang/{errors,evaluator,lexer,parser}.py`, mtime 15:42:06Z, carrying an
implementation of the feature under test) and one untracked file
(`fixtures/tests/test_comparisons.py`, mtime 13:21:53Z, a visible-suite test for the
feature). Every trial that staged after 13:21:53Z therefore started from a tree the bank never
declared: an extra visible test at first, the solution's parser/evaluator changes later.

Evidence, from the captured orchestrator streams (event timestamps; stream file names carry
the *end* time of a spawn):

- pilot-v2 `perpr-haiku` r1 (10:12:26–10:32:47Z): the orchestrator edited the four fixture
  files, ran the probes and `verify.py` against the fixture path, ran `git -C <task_dir>
  status` / `diff` (the diff listing included this pre-registration document), then ran
  `git checkout -- fixtures/exprlang/*.py`, restoring those four files before it ended. It
  reached the harness and the experiment's own documents; its result is unusable regardless
  of what its workspace scored.
- main-v2 `final-haiku` r3 (13:18:40–13:31:02Z): Edit calls on the four fixture files, a
  Write of `fixtures/tests/test_comparisons.py`, `unittest discover` run inside the fixture,
  and a `cp` of that test file into its staged workspace. It never restored the fixture.
- The 15:42:06Z write to the four `.py` files falls inside main-v2 `perpr-haiku` r4
  (15:30:35–15:42:37Z), whose orchestrator stream carries no fixture path: the write came
  from a subagent, whose tool calls the captured stream does not include. Inferred from the
  timestamp, not observed.

Root cause: the task directory is reachable from what the arms hand the orchestrator. The
perpr and placebo briefs pass `$FATHOM_TASK_DIR` explicitly (the driver's first argument);
every arm's `$FATHOM_PROMPTS_DIR` is `<task dir>/prompts`, so the parent is one path segment
away, and `fixtures/` looks like a project root (it holds `exprlang/` and `tests/`). The v1
pilot had already flagged a "driver-name visibility leak" through the same path; the
mitigation then (a prompts-only directory) hid the *listing*, not the *path*. Nothing checked
the fixture's integrity between trials, and nothing could exclude a recorded trial without
rewriting an append-only ledger.

### Disposition — 16 trial rows voided (`kind: void` rows appended to the ledger)

Voided, with the reason recorded on each void row:

- pilot-v2 `perpr-haiku` r1 — reached the harness (edited the fixture; read the
  pre-registration diff).
- main-v2 `final-haiku` r3 — edited the fixture; wrote the visible-suite test into it.
- every main-v2 trial that started after 13:21:53Z, i.e. staged from a modified fixture:
  `final-sonnet` r3, `perpr-haiku` r3, `perpr-sonnet` r3, `placebo-haiku` r3,
  `placebo-sonnet` r3, `control-haiku` r4, `control-sonnet` r4, `final-haiku` r4,
  `final-sonnet` r4, `perpr-haiku` r4, `perpr-sonnet` r4, `placebo-haiku` r4,
  `placebo-sonnet` r4, and `control-haiku` r5 (already `errored`: its verifier crashed when
  the fixture was restored under it).

Not voided: the 23 other pilot-v2 trials (all before 13:21:53Z; the pilot's `perpr-haiku` r1
restored the four files it edited before the next trial staged, and no later pilot trial
touched the fixture per its stream) and main-v2 `control-haiku` r3, `control-sonnet` r3.
Valid trials after the disposition: 25 (control 5+5, placebo 3+3, perpr 2+3, final 3+3 by
tier-set haiku+sonnet). Spend on the 16 voided rows ≈ $39; bank spend to date $96.56; program
spend $210.04 of the $400 iteration cap.

The exclusion is an *instrument* exclusion applied before any outcome of the affected trials
was read into a contrast: the void list is defined by a timestamp and two stream facts, not
by results. The `selection_exclusion` threat in the record moves from `controlled` to
`residual` with this addendum as its statement.

### Harness repair (before the first resumed trial)

1. fathom `void` rows: an append-only exclusion (`fathom void <bank> --scenario --repeat
   --reason --evidence`) that every reader honours in order (`ledger.apply_voids`): a voided
   trial is re-run on resume and the re-run counts. Nothing in the ledger is rewritten.
2. fathom fixture integrity guard: a manifest of the fixture tree is taken before any spawn;
   every trial is checked before it stages and after it returns; drift stops the matrix as
   an infrastructure failure, the trial that drifted is recorded `errored` (never scored),
   and every trial row now carries `fixture_sha`.
3. Harness directory: the runner script stages the five harness files (prompts, the driver,
   the probe, the placebo, `series.toml`) into a directory outside the repository and points
   `$FATHOM_TASK_DIR` / `$FATHOM_PROMPTS_DIR` there. No path an orchestrator or subagent is
   given now leads to `fixtures/`, `solution/` or `verify.py`. The arms' `config_hash` is
   unchanged: the `[env]` values are templates, resolved at spawn time by design.
4. The fixture was restored to its committed state at 16:58Z (`git checkout` of the four
   files, removal of the untracked test file and of `__pycache__` directories).

### The resumed plan, declared now

Budget remaining for this iteration: $189.96. At the pilot's $19.15 per pass, the voided
trials plus the passes still owed cannot reach n = 16 (≈ $245). **n is re-declared as 13 per
cell** (104 trials; 79 to buy ≈ $189; the runner stops at a bank spend of $286). The
contrasts, endpoints, Holm family, tier-set separation and one-sidedness are unchanged. Exact
power on the decisive contrast (perpr vs placebo, Laplace-shrunk pilot rates 0.875 vs 0.375,
alpha 0.0125) at n = 13 is **0.532** (perpr vs control, 0.875 vs 0.0625: 0.992), computed
with the same exact-Fisher script as the n = 16 declaration (0.688) before the first resumed
trial; a non-significant decisive contrast is reported as underpowered at the achieved n. Interleaving
stays pass-wise; the voided pass-4 and pass-5 trials are re-bought first (resume order).

Should the operator raise the cap, n returns to 16 by the same passes; the record's
`design.cells[].planned_n` stays 16 until the matrix closes and is then reconciled to the
achieved n with this addendum as the reason.

## Pre-registration — the hook arms (program 2, Part 2), before their first paid trial

**Written 2026-09-02, after convoy 0.12.0 shipped and before any hook-arm trial is bought.**
Two arms are added to bank `multiagent-composition-v2` in their own scenarios directory
(`scenarios/multiagent-composition-v2-hook/`), joining the same ledger: `hook-haiku` and
`hook-sonnet`. They are the mechanism arm the program-2 design (fathom
`docs/specs/2026-09-02-hook-gate-closed-loop-design.md`, Part 2) called for, updated for
what the build found.

### The mechanism under test

convoy 0.12.0's `convoy hook`, wired through user-scope settings injected into the spawn's
isolated config directory (`[settings] inject`), on two Claude Code events:

- `SubagentStop` — the judge. When an implementer subagent tries to stop, the project gate
  (the decomposition's own `[[checks]]` plus the two independent type-contract probes —
  the same composition the `perpr` driver builds, `assets/hook-gate.toml`) runs in the
  workspace, scoped to the PR's phase by a `[convoy-phase: <tag>]` marker in the subagent's
  brief. A blocking red is handed to the *subagent* as the reason it may not stop yet, with
  the repair brief; one repair round, then it may stop.
- `PostToolUse` on `Agent` — the messenger. On a synchronous dispatch, a residual red is
  shown to the orchestrator; on the Agent tool's default asynchronous dispatch (observed
  in the build's smoke: `async_launched`), nothing is shown at the tool call and the judge
  is the only leg. The arm does not tell the orchestrator how to dispatch.

The orchestrator's brief is control's with **one added instruction**: begin each subagent
prompt with the PR's phase tag as `[convoy-phase: <tag>]` (`assets/brief-hook.md`; the diff
against `brief-control.md` is that one numbered item). The marker is scope information for
the gate, not knowledge of a gate: the brief mentions no gate, no check, no repair. The
implementer's brief is the PR prompt verbatim, as in every arm.

What differs from control, exhaustively: that one instruction; `[settings]`; three `[env]`
keys (`CONVOY_GATE_SPEC`, `CONVOY_TRUSTED_ROOTS`, `CONVOY_ORACLES`). Same orchestrator
model and effort, tools, limits, the five inherited `[env]` keys, the same staged harness
directory outside the repository (the gate spec is selected by path and never copied into
the tree; the probe is the asset under the harness dir).

### Prediction and reading

- Primary endpoint unchanged: `held_out_clean`. Prediction, declared: `hook` ≈ `perpr` on
  `held_out_clean` (the same oracle and the same repair information reach the implementer),
  at **control's orchestrator turn count and tokens** (the gate loop leaves the
  orchestrator's context) — the cost claim of the design, tested against the cells that
  already exist. A secondary reading: the `hook` arm's repair happens inside the subagent
  (the judge blocks its stop), so `fixes` counted from the messenger are expected to be
  near zero while `hook.log` shows the judge's blocks.
- Contrasts, one-sided, Holm within the tier-set: (5) hook vs control, (6) hook vs placebo
  — added to the family as exploratory (the record's frozen family is the four contrasts;
  these two are reported beside it, labelled, not in the confirmatory Holm family of the
  frozen record). Decision rule for the mechanism: hook vs control supported at 0.05 AND
  hook's orchestrator turns within control's interquartile range → the hook mechanism is
  adopted as the default recommendation over the `perpr` driver loop for iteration 2.
- Attestation: per trial, `<tag>--hook.log` in the stream dir (copied by a `Stop` hook
  from the workspace's `.convoy/hook.log`): every judge and messenger firing with the
  verdict, the block, the model (dated), the spec hash and the workspace. A trial with no
  `hook.log` copy is an arming failure and is voided, not scored.
- An arming probe of one trial per cell (2 trials) precedes the passes: it is voided if
  its `hook.log` copy is missing, and counts as repeat 0 otherwise.
- n = 13 per cell, matching the re-declared main-matrix n; run as repeat passes after the
  main matrix closes, ≈ $2.4 per trial, ≈ $62 for both cells — inside the iteration cap
  only if the main matrix stops under its $286 bank ceiling; otherwise the hook arms run
  in the next iteration with their own cap. Caps: $20 per spawn, the same $275 run cap.
- Exclusion: the fixture integrity guard and the harness directory are in force; any drift
  stops the matrix and voids the trial, as for the main matrix.

## Correction — 2026-09-02 22:50Z, the incident addendum's budget arithmetic (before any trial beyond n = 13)

The incident addendum states the program spend at the incident as $210.04 and the remaining
budget as $189.96. Both are wrong by $57.46: the v2 pilot's spend was counted twice, once
inside the bank's ledger total ($96.56, which already includes the pilot's $57.46) and once
on its own. The correct figures at the incident: v1 pilot $56.02 + bank v2 $96.56 = **$152.58
spent, $247.42 remaining**. At the observed $2.4 per trial that remainder buys 103 trials —
exactly the 128 − 25 the frozen plan needs.

Consequence, declared now, while the matrix is at 48 valid trials and $154.19 on the bank
(pass 7 of the n = 13 schedule running): **n returns to the frozen 16 per cell.** The record's
`design.cells[].planned_n` needs no amendment; the disposition will count 128 completed
trials in the frozen cells, with the 16 voided rows outside the design as the incident
addendum describes. The runner's bank cap moves from $286 to $343 (program cap $400 less
the v1 pilot's $56.02) for passes 14–16, which at the observed rate end near the cap; if the
cap stops the last pass short, the achieved n is reported per cell and the shortfall is
the disclosed deviation, not a re-plan. The n = 13 power statement (0.532) is superseded by
the frozen declaration (0.688 at n = 16).

The hook arms pre-registered above no longer fit inside this iteration's cap once the main
matrix takes its full n; they run at the start of the next iteration under its own cap, as
their pre-registration already provides. The correction itself changes no arm, no brief,
no endpoint and no contrast.

## Run log — 2026-09-03 19:21Z, the main matrix closed

128 of 128 trials in the frozen cells completed (16 per cell, the frozen n); the ledger
carries 144 trial rows, the 16 voided at the incident among them. Bank spend $352.02,
program $408.04. The runner's bank cap ($343) is checked between passes and fired only
after the last one: pass 16 as a whole was projected at ~$352 before it started, about
$8 over the $400 iteration cap, and the user authorized the overage on 2026-09-03 at
18:08Z with three of its eight trials done (bank $338.66 at that moment). Two further
seat expirations stopped the runner — at the start of pass 12 (08:50Z) and at the start
of pass 16 (17:17Z) — both refused by the arming probe before any spawn; nothing was
lost or re-bought. No arm, brief, endpoint or contrast changed after the correction
above. Readout: `tools/readout_multiagent.py` (voids applied); typed record and derived
report: `experiments/multiagent-composition-v2/record.yaml` and `report.md`; findings:
`docs/reports/2026-09-03-multiagent-composition-findings.md`.

## Correction — 2026-09-03, after the blind review of the closed matrix

Two blind reviewers (methodology; decision relevance) read the closed record, its derived
report and the findings with no access to the authors, and ten of their fourteen serious
findings were adversarially verified by a third pass. The confirmatory numbers reproduced
to four decimals; the following statements in this document and its addenda do not stand
as written and are corrected here, in the dated form this file uses. Nothing below changes
an arm, a brief, an endpoint, a contrast or the frozen n.

1. **The sensitivity endpoint (addendum no. 4) is not what its definition says.** It was
   defined as "the conjunction of the four held-out criteria the hint and the probes do not
   touch". Two of the four grade the probes' own rule (`env_bool_typing` asks bool-in-
   arithmetic and bool-in-comparison through the environment; `error_type_is_typemismatch`
   grades the exception class the repair hint names verbatim, `TypeMismatchError`), and the
   other two (`not_precedence_heldout`, `short_circuit_heldout`) are at 16/16 in seven cells
   and 15/16 in placebo-haiku, so they carry no information. On the 128 counted trials the
   endpoint is numerically identical to `env_bool_typing` alone in every cell, and the primary
   endpoint equals the conjunction of the four bool-rule criteria in every cell. The
   experiment measures one defect class — booleans are not numbers — and cannot show that the
   gate's benefit extends to work independent of the rule it teaches. The disjointness the
   record cites (`tests/test_multiagent_bank.py::TestProbeDeOverlap`) asserts string
   non-overlap only. The record's verdict on the sensitivity endpoint is `inconclusive`.

2. **"No path an orchestrator or subagent is given now leads to `fixtures/`, `solution/` or
   `verify.py`" (incident addendum, harness repair item 3) is false for one arm.** The staged
   harness directory covered every arm's orchestrator and the whole of control, placebo and
   perpr from the first resumed trial. The `final-*` arms' `[gate].extra` command is expanded
   by the gated-session strategy from the bank's `task.task_dir` — the repository directory —
   and the fix prompt hands it to the fix spawn verbatim; it reached an agent whenever the
   gate went red (26 of the 32 counted final trials, 20 of the 26 after the repair). A scan of
   every post-repair final stream finds no read of `solution/` or of the real `verify.py`; the
   one realised traversal is final-haiku r3's fix spawn reading `run_convoy_gate.py` and
   `type_probe.py`. Subagent tool calls are not fully captured, so this bounds the residual
   without eliminating it. Threat `custom_harness_containment` in the record.

3. **The void rule was under-inclusive relative to its own root cause, and four counted
   trials touched the task directory.** The exclusion keyed on fixture mtime (13:21:53Z) and
   two named streams; it does not reach oracle reads through the same exposed path earlier
   that morning. `tools/stream_facts.py --exposure` over every counted trial's surviving
   stream finds four: perpr-sonnet r0 and r1 (an implementer subagent read `verify.py`; both
   held-out-clean), placebo-haiku r1 (read `verify.py`, `type_probe.py`, `run_convoy_gate.py`
   and the whole reference solution, implemented PR01 in the task directory, declared its own
   measurement compromised and ended after 2 of 5 dispatches; not held-out-clean) and
   final-haiku r3 (item 2). They are retained — voiding them now would be an exclusion chosen
   after their outcomes entered the contrasts — and reported with the sensitivity: dropping
   the first three leaves perpr > placebo at Holm 0.0007 (Haiku) and 0.0106 (Sonnet, 12/14 vs
   5/16) and moves final > placebo at Haiku from 0.0366 to 0.0531; dropping all four gives
   0.0697 (and final > control 0.0183). Scoring the two perpr-sonnet successes as failures
   leaves perpr > placebo at 0.0350. The per-PR conclusions survive every version; the
   final-vs-placebo Haiku contrast does not. Every count in this item is the output of
   `tools/stream_facts.py`, committed with this correction.

4. **The dose report addendum no. 5 requires was not produced at the readout; it is now.**
   From tool_use events on the surviving stream of each counted trial: gate reds per trial
   perpr 1.19 (Haiku; 13 trials at 1, 3 at 2) and 1.06 (Sonnet), placebo 0.94 and 1.06 (one
   red per fresh workspace by construction; the aborted placebo-haiku r1 never reached it);
   `Agent` dispatches per trial perpr 7.19 and 7.12, control 6.00 and 6.06, placebo 5.75 and
   5.94, final 6.00 and 6.00; executed driver calls per perpr trial 6 in 27 and 7 in 5. The
   counts do not diverge materially on reds, so the decisive contrast is reported as
   matched on gate-red count, not dose-confounded; on the other dose measures perpr still
   does more work than the placebo (about 1.2 more dispatches, about 10% more spend, 13–19%
   more wall-clock per trial on medians), so the extra-work channel is bounded, not
   eliminated. What the placebo does not match is the repair actor — perpr dispatches a
   fresh implementer subagent carrying the `repair_brief` (one extra dispatch per trial),
   placebo repairs inside the orchestrator — and the brief's content (perpr's block states
   that the gate adds type-contract checks the visible suite lacks; placebo's does not).
   Both are declared residual threats. In every one of the 26 final-arm loop firings the
   trigger was convoy's red with the task's own gate green on the first round (32 of 32);
   the visible suite went red only on the last round of four trials, after the fix spawns. The earlier mechanism
   figures ("7–8 dispatches, 8–9 driver invocations") were substring counts over
   concatenated stream files and are withdrawn.

5. **The tool allow-list the scenarios declare was not the instrument that ran.** Every
   stream's init lists the platform's registered tools — about thirty, including unrestricted
   Bash and PowerShell — identically across arms; `Bash(python:*)` was not enforced. That is
   the root cause of the fixture incident and of item 3, not only "a path the harness
   exposed". Iteration 2 verifies enforcement before its first paid trial.

6. **Smaller corrections.** The correction addendum above is headed 22:50Z; its commit
   (f2ff474) is 22:46:16Z. The record's `plan_frozen_at.timestamp` now carries the commit's
   own time (13:41:47Z). The typed record's void breakdown read "2 control … 5 final"; the
   ledger's is 3 control, 4 placebo, 5 perpr, 4 final. The per-trial cost and wall-clock
   figures in the findings are medians and are labelled so; cost per held-out-clean trial is
   the cell's total spend divided by its clean trials. The pooled pilot's 24 ran arm-blocked
   and 25 counted trials predate the fixture guard (no `fixture_sha`); both are listed among
   the deviations. `full15_clean` was pre-registered as the secondary endpoint and is
   recorded as exploratory; it is not the implementer's visible suite and is no longer
   described as such.

## Pre-registration — iteration 2 on bank v2: contemporaneous cells, the equal-content placebo, the gate as a hook

**Written 2026-09-03, before any iteration-2 trial is bought.** The operator authorized a
new cap of $400 for this iteration on 2026-09-03, after the iteration-1 readout and its
blind review. Iteration 1's cells are not reused as comparison cells here: every contrast
below is between cells bought in the same interleaved passes.

### What iteration 1 left open, and which of it this iteration answers

The blind review of iteration 1 narrowed its claim to what was shown: the per-PR gate
restored the one rule bank v2 withholds, the placebo matched the gate's red count but not
the repair actor (perpr dispatches a fresh implementer with the `repair_brief`; placebo
repaired inside the orchestrator) nor the brief's content (perpr's block says the gate
adds two type-contract checks the visible suite lacks; placebo's says nothing of the
kind), and the tool allow-list the scenarios declared was not enforced at the registry
level. Iteration 2 answers three questions on the same bank and fixture:

1. **Is the gate's information the cause, beyond the brief's content and the repair
   actor?** An equal-content placebo (`placebo2`) whose brief is the per-PR treatment
   brief byte for byte except the gate command, and whose gate returns the same envelope
   shape with no information, forces the same fresh fix-subagent dispatch.
2. **Does the gate keep its effect when the orchestrator is told nothing about it?**
   The hook arms (`hook2`): convoy 0.12.0's `SubagentStop` judge and `PostToolUse`
   messenger, armed through injected settings; the orchestrator's brief is control's plus
   the one-line phase marker.
3. **Does the iteration-1 result replicate on contemporaneous cells under an enforced
   tool registry?** `perpr2` against `control2`.

Not done here, deliberately: a second defect class on exprlang (the inhouse-lib bank,
pre-registered separately, is the generalization test); the fixture's test docstring
naming `verify.py` stays as it is (the fixture's identity is the bank's; the exposure scan
is the guard); the `${task_dir}` expansion of the final arm's gate command is moot (no
final arm here).

### Cells

Eight, bought in interleaved repeat passes, n = 16 each, all on `tasks/multiagent-composition-v2/exprlang`
with `dataset_version` unchanged and the fixture byte-identical to iteration 1
(`fixture_sha` on every row). Scenario TOMLs under `scenarios/multiagent-composition-v2-iter2/`.

| cell | orchestrator brief | gate | who repairs a red |
|---|---|---|---|
| `control2-{haiku,sonnet}` | iteration 1's control brief, byte for byte | the project's visible suite only | the orchestrator, as it sees fit |
| `placebo2-{haiku,sonnet}` | the per-PR treatment brief with the gate command swapped for `placebo_gate2.py` — every other byte equal, including the sentence about two type-contract checks | an envelope-shaped placebo: `blocked` once per workspace with a `repair_brief` naming no check, no file, no type, no rule; `completed` afterwards | a fresh fix subagent dispatched with that `repair_brief` verbatim, as in perpr |
| `perpr2-{haiku,sonnet}` | iteration 1's per-PR treatment brief, byte for byte | `run_convoy_gate.py --phase <pr> --json` — the decomposition's own checks plus the two independent type-contract probes, convoy pinned at `v0.12.0` | a fresh fix subagent dispatched with the envelope's `repair_brief` verbatim |
| `hook2-{haiku,sonnet}` | control's brief plus one numbered item: begin each subagent prompt with `[convoy-phase: <tag>]` | the same gate spec (`assets/hook-gate.toml`) run by convoy 0.12.0's hook: the judge blocks the implementer's stop once with the repair brief; the messenger reports a residual red to the orchestrator on a synchronous dispatch | the implementer itself, inside its own dispatch; the orchestrator only on a residual red it is shown |

Implementer tier is the second factor: `FATHOM_IMPL_MODEL` = `claude-haiku-4-5` or
`claude-sonnet-5`. Orchestrator `claude-sonnet-5`, effort high, in every cell. Tools,
limits, the shared `[env]` keys and the staged harness directory are identical across
the eight; the documented differences are the brief, the gate command, and for `hook2`
the `[settings]` injection plus the three `CONVOY_*` keys the hook needs. A test
(`tests/test_multiagent_iter2.py`) asserts the byte-identities and the exact diffs.

### What changed in the harness since iteration 1, for every cell alike

- **Registry-level tool restriction.** Each scenario sets `[tools] registry = "allowed"`,
  which makes fathom pass `--tools` with the allow-list's bare names (Read, Write, Edit,
  Glob, Grep, Agent/Task, Bash) beside the unchanged `--allowedTools` pre-approval
  (`Bash(python:*)`). The arming probe asserts the init event's registry is that set;
  iteration 1's streams listed about thirty tools.
- **Timestamps.** Trial and run rows carry `started_at` and `ended_at` (UTC), so the
  chronology below is read from the ledger, not from stream file names.
- **One convoy release for both treatment forms.** `run_convoy_gate.py` reads
  `FATHOM_CONVOY_PIN` (default unchanged, `v0.11.0`; iteration-1 rows are reproducible)
  and every iteration-2 cell sets it to `v0.12.0`, the release whose hook the `hook2`
  arms run. The effective pin is echoed on every call, so each trial's stream attests it.
- **The cap is a forecast, not a post-mortem.** The runner (`local/run-iter2.sh`) stops
  before a pass whose forecast cost (the mean of the completed passes on these cells)
  would take the iteration's bank spend past $385, and exits without starting it.
  Iteration 1's cap was checked after the pass that crossed it.
- **Exposure is a per-pass gate.** After every pass `tools/stream_facts.py
  --fail-on-exposure` scans the pass's streams for any read, write or command naming the
  bank's task directory outside `prompts/`; a hit stops the runner before the next pass.
- **Arming is checked on pass 1, per arm**, from the streams and the hook log (below).

### Endpoints

- **Primary, confirmatory:** `held_out_clean` — the conjunction of the six held-out
  criteria of `verify.py` (hash `78d0e86d…`, unchanged), graded blind to arm on the
  executed workspace. As iteration 1 established, on this bank it measures one defect
  class (booleans are not numbers); this iteration does not claim otherwise.
- **Secondary, exploratory:** `full15_clean`.
- **Mechanism and dose, from the streams and `hook.log`:** Agent dispatches per trial,
  executed driver calls and reds (`perpr2`), placebo reds (`placebo2`), judge firings and
  blocks (`hook2`, from `<tag>--hook.log` copied by the Stop hook), orchestrator turns
  (run rows), cost per trial, wall-clock, cost per held-out-clean trial (cell spend over
  clean trials).

### Contrasts

Fisher exact, one-sided treatment > comparison, Holm within each tier-set's family of
four at alpha 0.05, tier-sets never pooled:

1. `hook2` > `control2`
2. `hook2` > `placebo2`
3. `perpr2` > `placebo2` — the mechanism-independence test
4. `perpr2` > `control2` — the replication

Outside the family, labelled as such wherever printed: `hook2` vs `perpr2` on
`held_out_clean` (two-sided Fisher and a Newcombe 95% interval on the rate difference;
descriptive at n = 16, no non-inferiority claim is licensed at this n); `placebo2` >
`control2` (one-sided; the brief-content and fresh-repair channels alone); cost per trial
and orchestrator turns, `hook2` vs `perpr2` and `hook2` vs `control2`, Mann-Whitney U
two-sided on the per-trial values with medians and interquartile ranges.

### Readings, declared now

- **Mechanism (contrast 3).** Supported at both tiers: the gate's information causes the
  gain beyond the brief's content and the repair actor, and iteration 1's claim stands
  with that channel closed. Not supported at a tier with `placebo2`'s rate within 0.15 of
  `perpr2`'s: the brief's content and the fresh repair explain iteration 1's win at that
  tier, and the "independent information" claim is withdrawn there — published as such.
  Not supported with a larger gap: underpowered at n = 16, reported as such.
- **Hook adoption (contrasts 1 and 2 plus dose).** Both supported at both tiers, and
  `hook2`'s median orchestrator turns at or below `control2`'s upper quartile, and
  `hook2`'s median cost per trial at or below `perpr2`'s: the hook form becomes convoy's
  recommended default over the driver loop, in convoy's own docs through its own process.
  Any of these failing: the driver loop stays the recommendation and the hook's result is
  reported at its weight.
- **Replication (contrast 4).** Supported at both tiers: iteration 1 replicated on
  contemporaneous cells under the enforced registry. Not supported: reported beside
  iteration 1's cells with the two harness differences named.

### n, power, passes, budget

n = 16 per cell, 128 trials. Exact power for a one-sided Fisher test at alpha 0.0125
(Holm's strictest step), computed with `local/power_n.py` before the first trial: at
Laplace-shrunk iteration-1 rates 0.94 vs 0.39 (perpr vs placebo) the decisive
mechanism contrast has power 0.855 (0.809 at 0.90 vs 0.35); `hook2` > `control2` at 0.90
vs 0.20 has 0.968; `hook2` > `placebo2` at 0.90 vs 0.39 has 0.737.
A non-supported contrast at n = 16 is reported as underpowered at the achieved n, never
as a null. Passes `k = 1..16` with `--repeats k`, each covering the eight cells once, so
arms are interleaved by pass and time is not confounded with arm. Forecast cost per pass
$19.7 from iteration 1's medians (control $1.93 and $2.28; the three gated arms taken
at perpr's $2.31 and $2.85), 16 passes about $315; arming probes under $1. The runner's
forecast rule stops before the pass that would take the iteration's bank spend past
$385; the operator's cap is $400. If the cap stops the matrix short of 16, the achieved
n is reported with a `design.amendments` entry and no cell is topped up afterwards.

### Arming, exclusions, chronology

- **Arming criteria, evaluated on pass 1 per arm before pass 2 starts**, from
  `tools/stream_facts.py` and the hook log: `control2` — zero driver calls, zero placebo
  calls, no hook log; `placebo2` — at least one placebo red and zero driver calls;
  `perpr2` — at least five executed driver calls and zero placebo calls; `hook2` — a
  `hook.log` copy present in the stream dir and zero driver calls at the orchestrator.
  A failed criterion stops the runner; the trial is voided (`fathom void`, reason
  recorded), the defect is fixed in the harness, and the key is re-bought. An arm whose
  mechanism cannot be armed is dropped by a `design.amendments` entry, never mutated.
- **Exclusions, mechanical:** a trial the per-pass exposure scan flags (any read, write
  or command naming the task directory outside `prompts/`) is voided before the next pass
  and re-bought; a `hook2` trial without a `hook.log` copy is voided and re-bought; an
  `errored` row is not counted and its key is re-bought by the next pass; fixture drift
  stops the runner and voids the trials the guard names. Seat expiry stops the runner at
  a trial boundary and the same command resumes; nothing is excluded for it.
- **Chronology:** this addendum and the typed record
  `experiments/multiagent-composition-v2-iter2/record.yaml` are committed before the
  first trial, with `plan_frozen_at.commit` pointing at the record's own commit, so the
  chronology gate (ER-ANCHOR) is expected to pass; the first trial's `started_at` on its
  ledger row is the check.
- **Readout and review:** `tools/readout_multiagent.py --family iter2` prints the cells,
  the four contrasts with Holm, the labelled extras, the dose table and the exposure line;
  the record is filled from it, validated and rendered; two blind reviewers read the
  findings before any claim is made; a loss is published as a loss.
