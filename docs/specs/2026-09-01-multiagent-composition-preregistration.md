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
