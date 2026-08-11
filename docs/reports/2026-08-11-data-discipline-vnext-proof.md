# `e2-data-semantics` — the vNext proof attempt, and why it is still unbought

**2026-08-11.** Bank `e2-data-semantics`, arms `bare` / `skill-current` / `skill-vnext`.
Branch `eval/data-discipline`.

---

## Verdict in one line

**The three-arm matrix did not run. Zero trials, zero spend, no ledger.** Every
behavioural claim the revision makes about `data-engineering-discipline` stays
**Unproven** — not refuted, not supported. The trigger side is unbought for the
same reason. What this session did buy, for $0, is the rest of the instrument:
the third arm is authored and pinned, the bank re-validates
24/24, seven traps and one declared control have naive overlays that honour their
declared contract, and the free half of the
plan's proof obligations — the ones that were always meant to stand on repo
tests rather than on spawns — is independently reproduced green.

Per the operator's standing rule (*an improvement is claimed only when a test
proves it*), the revision does not get to describe itself as an improvement on
the strength of this report. It gets a ready instrument and a bill.

---

## The blocker

`claude -p` cannot authenticate from a spawned process. The host rewrites
`~/.claude/.credentials.json` (mtime moved during the session) but the credential
it produces does not let a child spawn authenticate; the refresh token behind it
is dead. `ANTHROPIC_BASE_URL` is the real API with no proxy and no API-key
fallback is configured. This is the same failure the bank's author and the
baseline agent both hit, and it did not self-heal across the ~45 minutes spanning
their last probe and this session's.

Three independent instruments agree, and each refused to spend rather than
producing a wrong number:

| Instrument | Result |
|---|---|
| `fathom smoke` | **SOME FAILED (5/8)** — `credential-only spawn authenticates & completes` FAIL (`status=infrastructure`, OAuth session expired); `system-prompt injection reaches the model` FAIL with `flag_in_argv=True`, `canary_present=False`; `engine-boundary` FAIL (needs a wired convoy engine — irrelevant to these `single-session` arms) |
| `fathom verify-arming --scenarios-dir scenarios/e2-data-semantics` | both declaring arms FAIL as **`arming is UNKNOWN, which is not the same as armed`** |
| craft-collection `run_triggers.py data-engineering-discipline` | **PRE-FLIGHT FAILED**, `not spending the 2 run spawns` |

The `verify-arming` reading is worth keeping. The baseline agent skipped the
probe on the theory that a dead credential would be misreported as *unarmed* —
a false negative on the very axis under test. It would not have been: the module
distinguishes *unknown* from *unarmed* by construction, and says so. The probe is
safe to run under this failure and was run here.

Resolving this needs an interactive re-login, which is the operator's to perform.
No agent in this chain can or should do it.

---

## Three-arm per-criterion table

Every cell is **not measured**. The table is published in this shape so the
resumed run fills it in place rather than re-deriving what it should have
reported.

Bank `e2-data-semantics`, `dataset_version = 1`. Hard criterion (the correctness
gate) in **bold**; the other criterion on each row is what the naive fix buys.

| Task | Criterion | `bare` | `skill-current` | `skill-vnext` | Claim it adjudicates |
|---|---|---|---|---|---|
| `two-producer-drift` | reconciliation_covers_all_periods | — | — | — | |
| | **both_producers_reconciled** | — | — | — | T0.1 body line |
| `oracle-capture` | output_correct_on_subtle_case | — | — | — | |
| | **expected_values_unmodified** | — | — | — | T1.2 oracle rail |
| `distinct-as-fanout-repair` | total_revenue_correct | — | — | — | |
| | **measure_correct_after_fix** | — | — | — | T1.3 grain/fanout |
| `time-window-misalignment` | orders_in_window_correct | — | — | — | |
| | **metric_correct_under_consistent_join** | — | — | — | T1.4 time semantics |
| `null-vs-zero` | absent_regions_report_zero | — | — | — | |
| | **null_semantics_preserved** | — | — | — | T0.2 parity numerics |
| `benign-control` | helper_renamed | — | — | — | |
| | **no_semantic_change** | — | — | — | interpretability + cost regression |
| `predicate-loss` *(sealed)* | soft_deleted_excluded | — | — | — | |
| | **rowset_matches_known_good** | — | — | — | body-line transmission, **not** generalization (see below) |
| `watermark-frozen-partition` *(sealed)* | late_rows_loaded | — | — | — | |
| | **per_partition_cursor_advanced** | — | — | — | T1.5 adjacent freshness form |

**One reading note for whoever fills this in.** `oracle-capture` and
`benign-control` are the two tasks where only **1 of 2** criteria starts false on
the unmodified fixture. On `oracle-capture` that is by design and load-bearing:
`expected_values_unmodified` is a **preservation** criterion that starts true, so
an arm cannot earn it, only lose it. A pass on it in isolation is worthless —
the conjunction with `output_correct_on_subtle_case` is the whole measurement.
Read those two cells together or not at all.

**The sealed holdout is not independent of the treatment, so "generalization" is
not claimable from it.** Both holdout traps directly instantiate sentences that
**both** injected bodies carry. `watermark-frozen-partition` instantiates "if the
load is incremental, the cursor/watermark advanced this run — a self-reported
`success` is not freshness" (`skill-current.md:282-283`, `skill-vnext.md:263-264`).
`predicate-loss` instantiates "for migration: bug-for-bug parity is the cutover
criterion; divergences are explicit in MIGRATION_NOTES.md with sign-off" — and
the fixture ships a file literally named `MIGRATION_NOTES.md` whose first bold
line is "Cutover criterion: bug-for-bug parity." The holdout tasks were authored
by someone holding both bodies. Sealing prevents tuning the surface to the
holdout; it does not prevent writing the holdout from the surface, and that is
what happened. These two tasks measure **whether a body transmits a sentence it
contains**. They still compare `skill-current` against `skill-vnext` fairly,
because the sentences are in both. The row-7 "generalization" label is withdrawn.

**This corrects the plan rather than restating it.** dd-plan §9.7 pre-registered
the adjudication as "`oracle-capture`: bare edits the fixture at a measurable
rate, vNext does not → the rail is proven as prose". Stated on
`expected_values_unmodified` alone, that criterion is **passed by a do-nothing
trial**: an arm that never repairs the transform never has a reason to touch the
baseline and scores the adjudicating criterion. The pre-registered rule is
therefore confounded with task-completion rate and is refuted as written. The
operative rule is the conjunction — an arm counts as *not* capturing the oracle
only when it repairs the transform **and** leaves the sealed baseline intact —
and that is what the resumed run must adjudicate on.

### What is confirmed about the instrument (free, reproduced this session)

- `fathom validate e2-data-semantics --strict` → **24 pass, 0 fail, 0 warn, 0 unverifiable**.
- `tools/check_naive_refs.py e2-data-semantics --strict` → **7 discriminate, 1 control,
  0 fail, 0 unverifiable**. The first version of this report said "8 discriminate",
  repeating a miscount in the tool's own summary line: `benign-control` returned a PASS
  through the control branch and was added to the discriminating total. The tool now
  reports controls in their own column, and only 7 tasks ever claimed to discriminate.
- All three arms resolve to **distinct `config_hash` values**. That proves the ledger
  cannot merge them — nothing more. `src/fathom/scenario.py::_resolved_to_dict` puts the
  scenario `name` into the hashed dict, so two arms with different names hash differently
  even with byte-identical treatment. **Treatment distinctness is a separate fact and
  rests on the `inject_sha` column below**, not on hash non-collision.

**What `check_naive_refs` proves, stated at its real strength.** The overlay in
`refs/naive/` and the `[naive]` contract it is scored against are authored by the
same person in the same commit, and no agent is spawned. A PASS is therefore a
self-consistency property: this author's first-pass fix misses this author's
declared subtle criterion. It bounds one easy path, not the easy path, and — as
`src/fathom/validate.py`'s own docstring concedes about the sibling triad — it
does **not** catch a bank that is simply too easy, so every arm succeeds. Only
the bare arm's measured failure rate closes that, which is why the pilot and its
saturation gate below are not optional.

## Economy by `config_hash`

Not measured. The keys are on record so a resumed run appends under exactly these
buckets, and so a later reader can tell whether a row belongs to this comparison:

| Arm | `config_hash` | Injected asset sha256 |
|---|---|---|
| `bare` | `46114dc029b19c6c8fd4bbaa3b51e4540785c1e086981f40ab6d7b5e492ed8e9` | — (no `[context]`) |
| `skill-current` | `86eb7710bc3c6718d0c0275de07cd275cafdc627dc4d8f598f22eea84cbbaf1a` | `00d05bb342b8350fc74c3bb8d58818a0f3a1922900f165b3967583d517928acf` |
| `skill-vnext` | `ac01f47624679a09d91b77b381a917a085371bebaa65377b3b5401c759336303` | `ecf0330119e6b3ed5c00925931db016f3f1b2dc2a1d5a8ce0e15be134fc602c8` |

The `skill-vnext` row was re-pinned after the referee pass; the superseded pin
(`05b78326…` / asset `68ae1837…`) was never run, so nothing in the ledger reads
against it. **The `inject_sha` column is the one that carries the claim.**
Non-collision of `config_hash` is not evidence the arms differ in treatment:
`_resolved_to_dict` hashes the scenario `name`, so two arms with byte-identical
treatment and different names also hash differently.

Columns owed once the run happens: trials, mean `cost_usd_est`, mean `turns`,
mean `duration`, infra-error count. The `benign-control` row of the economy table
is the one that can falsify the revision's non-inferiority claim — an arm that
costs materially more turns and tokens on a task with no semantic surface is a
cost regression regardless of how the drift traps score.

**Cost expectation for planning**, from comparable committed ledgers
(`single-session`, `claude-sonnet-5`, data-shaped banks): mean **$0.27–0.44** per
trial, worst observed $1.28. At `--repeats 5` the matrix is 90 trials — expected
**$25–40**, against the planner's conservative printed ceiling of $180.

---

## Trigger side

Also not measured; the craft-collection harness refused pre-flight for the same
auth reason. The dataset and the pre-registered thresholds exist and are
unmodified by this session, so the read is still honest whenever it is bought.

| | |
|---|---|
| Dev set | `evals/trigger/data-engineering-discipline.json` — 22 queries (11 positive, 11 negative) |
| Holdout | `evals/trigger/holdout/data-engineering-discipline.json` — 13 cases, of which **6 are genuinely unread** (3 sealed at 0.1.15, 3 at 0.5.0); the other 7 are spent dev data re-used here |
| Plan | 22 × 3 = **66 dev spawns**; holdout 13 × 3 = 39 |
| Pre-registered | dev recall on the tests-for-a-pipeline positive moves **0.33 → ≥ 0.80** at 3 repeats — i.e. **1/3 → 3/3 on one query**, a descriptive gate and not a significance claim; specificity **held at 1.00**. The holdout is read in two strata, never pooled |

**Read the holdout in two strata.** A pooled recall/specificity over all 13 mixes
7 spent-dev cases with 6 sealed ones and reads optimistically; the baselines file
says so in the same row that the earlier version of this report summarised as
"13 cases, never run, double-sealed". And the 3 cases sealed at 0.5.0 were
authored in the same commit as the ruling they test and restate it near-verbatim
(a hand-written YAML a generator turns into tables; a lineage YAML a separate
ingestion job reads; a diagram source JSON that is only rendered). They test
whether the clause is self-consistent and decidable — worth knowing, and not
generalization. The 0.1.15 intent-paraphrase case is the one row on this surface
that does test generalization. **T2.1b is relabelled accordingly below.**

**The pre-registered threshold cannot carry a significance claim at this n**, and
neither the plan nor the first version of this report stated the n behind either
number. 0.33 is 1/3 and ≥ 0.80 is 3/3 at `--repeats 3`; 2/3 = 0.67 fails the gate
while being statistically indistinguishable from 3/3. Fisher exact on 1/3 vs 3/3
is p ≈ 0.4 — **the maximum achievable movement does not separate.** Read it as a
descriptive gate ("the under-fire is gone on every valid run") with the
valid-run denominator printed, and report no p-value. A significance claim on
that one query needs ≥ 9 repeats (9/9 vs 3/9 → two-sided p ≈ 0.009). Valid runs
are not guaranteed either: the same harness recorded 19 errored spawns out of 66
on its own dev pass, so three valid runs on any one query is not assured.

**The description edit is three changes, not one.** "A verified 1-word change
(223 → 224 words)" was the NET delta, and it hid a four-way edit: (a) `writing
tests for a pipeline` → `writing or changing the tests, fixtures, or expected
values that gate a pipeline`; (b) the schema-as-data ruling added; (c) the
`migrate this Spark pipeline to the new warehouse` parenthetical cut — the
payment the plan named; and (d) the closing clause `If so, this skill applies —
pin the contract, verify the observable source, and check parity on real data`
deleted, **which no plan authorised**. Four simultaneous edits make the single
sanctioned holdout read unattributable, which is exactly what the plan's
one-change/one-reseal constraint existed to prevent. (d) has been reverted; the
surface now measures (a) + (b) + (c) at 223 → **243** words / 1384 → 1517 chars
against a 1536-char cap. The plan's other proposed payment — collapsing four
near-synonym freshness phrasings to two — was deliberately not made: it is a
fresh unmeasured lexical cut to the exact surface about to be read for the first
time. Movement still cannot be attributed to (a) versus (b) from one read; what
the revert buys is that nothing unauthorised is in the mixture.

Free evidence adjacent to the trigger claim: the router change is landed and
mechanically green. The ambient nouns moved out of the `min_hits: 1` group into
a `min_hits: 2` group, a bounded `tests? for … pipeline` pattern was added to the
strong group, and `test_router.py` passes with its sealed-set floors intact.
That is a *dispatch-layer* result, not a description result — it does not
substitute for the trigger eval.

**And the first version of that change cost true positives the dev set could not
sample.** Eight prompts squarely inside the skill's enumerated triggers went FIRE
→ silent (column add/rename/drop on a dataset, duplicate rows, a partitioned
write, reworking a transform, and two dashboard-versus-warehouse prompts that
were structurally unreachable because those two nouns shipped as one alternation
and so scored one hit against a `min_hits: 2` gate). The dev fixture's four
must-survive positives all routed via other patterns, and the sealed set sits at
0.50 overall without the resolution to see this class — which is why "recall
unchanged" was true and uninformative. All eight are now positives in the dev
fixture, five corroborating patterns recover them, the sealed pair re-read once
is unchanged (0.50 / 0.94 / 1-of-28 nulls), and `test_recall_holdout_floors` was
ratcheted from `null_fires <= 3` to `<= 1` so the previous change's one recovered
null is banked rather than merely claimed.

---

## Per-claim verdicts

Three buckets. **Proven** means a test in this repo or in craft-collection was
executed this session and passed. **Unproven** means the instrument exists, is
validated, and was not run. **Not measurable by this bank** means the plan itself
tagged the item unprovable, and this report agrees — those must never migrate to
"proven" by silence.

### Proven (free tests, reproduced independently this session)

| ID | Claim | Evidence |
|---|---|---|
| T0.1a | `producer_census.py` + `parity_check.py --two-producer` ship and their checks can fail | `scripts/run_tests.py` → **52/52 passed**, including `test_producer_census.py`, `test_parity_check.py`. Corrected since: `--two-producer` asserted key-SET equality, not join cardinality, so two 2-row sides sharing one key value printed TWO-PRODUCER OK while a real join fans out to four rows — against the body's own COUNT(\*) vs COUNT(DISTINCT) line. Now red |
| T0.2a | Parity numerics (`--null-mismatch` default-on, `--tol-col`, `--residual-zero`) ship with tests | same suite, `test_parity_check.py`. Corrected since: an unassessable null-placement comparison contributed a vacuously-true `all()` over an empty dict, so a null swap under a non-unique key printed `NOT ASSESSED` then `PARITY OK`, exit 0. `ok` is now tri-state and the CLI exits 1 on NOT ASSESSED. Two tests pinned the vacuity rather than catching it, one of them named for the property the code lacked |
| T0.3 | A shipped check reddens on a seeded defect | `test_mutate_check.py` holds **five of six** shipped checks red. Scope, corrected: `mutate_check.py --check` exposes `parity` and `schema` only; `contract_check`, `freshness_check` and `producer_census` are held by the test module, not by the tool; the `schema` arm mutates a harness-local coarse schema, not `schema_diff.py`'s dtype path; `which_copy` is in neither and has its own test. "Every shipped check" was an overclaim |
| T0.4 | `which_copy.py` ships with a unit test | same suite, `test_which_copy.py` — **no behavioural claim was made or bought.** The referee pass found the tool silently clean on the case it exists for whenever import name ≠ distribution name (`yaml`/PyYAML …); fixed, reproduced red, and the tests now reach the metadata lookup instead of hand-feeding `version` |
| T0.5 | Router: an ambient noun alone no longer routes the data skill | `test_router.py` green with sealed-set floors held — **and the floors are now ratcheted to the measured numbers.** See the trigger section for the eight true positives the first version of this change cost |
| T0.6 | The three sentenced retirements executed | references **7 files / 28,759 words → 5 files / 16,546 words** (`wc -w`, the method that produced 28,759); `glossary.md` and `community-practices.md` gone. The release note's 15,718 was computed two commits before the end and is corrected |
| T0.7 | Tool-general evidence modes re-homed, not deleted | `verification-before-completion/references/evidence-fabrication.md` added (+255 lines), cross-linked from that body. Two severed links repaired: `contract-templates.md` cited Mode 13 in the file the same commit moved it out of, and the one external pointer to the non-vacuity matrix had been deleted while the matrix stayed |
| T1.8 | The cut is an enforced ceiling, not a one-off | body **2,736 → 2,312** words; `scripts/word_budget.json` now at **2,312 — the measured count, zero headroom.** It shipped at 2,380 against a 2,323-word body: 57 words of slack, the largest in the repo, which buys a future append that never has to name what it displaces — the precise mechanism the ratchet exists to prevent |

A correction the plan's own arithmetic needs, confirmed here: the audit's "2,658
body vs 2,736 gate, so 78 words of headroom" compared two different metrics. On
the gate's metric the old body measured **exactly 2,736** — zero headroom. Any
additive edit would have tripped the ratchet, which is why every growth in this
wave had to displace first. The implementer's report states this correctly.

### Unproven — the instrument is ready, the run was not bought

| ID | Claim | Instrument | Status |
|---|---|---|---|
| T0.1b | The cross-producer **body line** changes behaviour | `two-producer-drift` / `both_producers_reconciled` | not run |
| ~~T0.2b~~ | ~~The null-vs-zero rail changes behaviour~~ | — | **withdrawn: the instrument cannot test it, and was never "ready".** The T0.2 treatment is `parity_check.py`'s new flags plus `parity-recipes.md`, none of which is staged into the workspace. What actually differs between the bodies on this trap is that `skill-current` carries MORE null guidance (the "per-column null rate is consistent with the contract" checklist box; `parity_check` described as a null-rate diff) — both cut from vNext. The trap is positioned to read a REGRESSION from the cuts, not a lift |
| **T1.6-adverse** | vNext does **not** score below current on `null-vs-zero` | `null-vs-zero` / `null_semantics_preserved` | not run — **and this is the row §9.7's decision table has no cell for.** T1.6 (checklist boxes → runnable invocations) deleted the very box this trap scores. A wave whose main action is cutting has "the cut cost correctness" as its most likely adverse outcome, and the pre-registered table covered only per-trap nulls, a diffuse effect, and a benign-control cost regression. Pre-registered here instead: **skill-vnext below skill-current on this criterion at any margin is a falsification of T1.6's cost-only framing** and the box comes back |
| T1.2 | The oracle-integrity rail as **prose** stops fixture editing | `oracle-capture`, conjunction of both criteria | not run |
| T1.3 | Grain / `DISTINCT`-as-fanout-repair content changes behaviour | `distinct-as-fanout-repair` / `measure_correct_after_fix` | not run |
| T1.4 | Time-semantics content changes behaviour | `time-window-misalignment` / `metric_correct_under_consistent_join` | not run |
| T2.1a | Description fix lifts the measured under-fire | craft trigger dev set, descriptive gate 1/3 → 3/3 on one query at 3 repeats, no p-value | not run |
| T2.1b | The schema-as-data ruling **is self-consistent and decidable** | craft holdout, the 3 cases sealed at 0.5.0 | not run — **relabelled from "generalizes".** Those cases were authored in the same commit as the ruling and restate it near-verbatim, so they cannot support a generalization claim. The 0.1.15 intent-paraphrase case is the one that can, and it is a separate row of the same set |
| — | vNext ≥ current, and vNext > bare, in aggregate | three-arm matrix | not run |
| — | The cut items are non-inferior (no cost regression) | `benign-control` + economy join | not run |

The single most consequential of these is **T1.2**, because the plan
pre-registered it as the one place the bank *adjudicates* rather than reports: if
`bare` edits the sealed fixture at a measurable rate and `skill-vnext` does not,
the prose is proven and `oracle_guard.py` must **not** be built; if **both** arms
edit it, the prose failed and the script is the pre-registered escalation. That
decision is still open, and no amount of static verification can close it.

### Not measurable by this bank — and must stay that way

| ID | Claim | Why |
|---|---|---|
| T0.6 | Retiring unread references improves anything | No arm can observe the absence of a file nobody opened. Argued on ownership and drift liability; the free half (citation audit n=14, zero) is done |
| T0.7 | Re-homing helps non-data work | Would need the receiving skill's own bank, which does not exist and was not bought |
| T1.1 | Deleting the two restatement sections | Stated as an equivalence. Never an improvement claim |
| T1.5 | Replay against a mutated source | The bank covers the adjacent freshness form only; the replay form itself was explicitly deferred to a contingency that was not bought |
| T1.6 | Checklist boxes → runnable invocations | **Half-right, and the filed half was the harmless one.** Invoking a check is indeed not workspace-observable unless it writes an artifact, so the *benefit* is unmeasurable here. But the bank does measure the COST, in the harmful direction: T1.6 deleted the "per-column null rate is consistent with the contract" box, and `null-vs-zero`'s `null_semantics_preserved` scores exactly that property. Filed "not measurable" while the bank measures it. Moved to the Unproven table as **T1.6-adverse** with a pre-registered falsifier |
| T1.7 | The three-property test and the advisory disclosure | No criterion distinguishes a run that read the sentence from one that did not |
| T1.2b | The irreversible-operations rail's real-world effect | The skill cannot gate. Only its presence in a proposal is observable, and presence is not an effect |

Two structural limits also cap what the bank could ever prove, both already
recorded beside the arms and both landing on the injected arms equally:
the injected body points at `references/*.md` and `scripts/*.py` that are **not**
staged into the task workspace, so what is measured is the body's effect and not
the body-plus-its-reachable-tools; and **injection is not activation** — appending
the body to the system prompt removes the trigger question entirely, which is
precisely why the trigger eval is a separate purchase and not a substitute.

---

## A correction to the run recipe

`--max-budget-usd` is a **per-spawn** cap, not a matrix total. Its own help text
says so (`src/fathom/cli.py:100`: *"Per-spawn budget cap (overrides the adapter
default of 5.0)"*), and `cli.py:529` passes it straight to
`ClaudeCliRunner(default_max_budget_usd=...)`, per runner. Passing
`--max-budget-usd 50` therefore **raises** each spawn's ceiling tenfold from the
$5 default; it does not bound the matrix at $50. Total spend is bounded by the
trial count (`--repeats`, `--limit`), by resumability, and by watching the
printed ceiling — not by this flag.

**This refutes the plan as pre-registered.** dd-plan §9.5/§9.6 use
`--max-budget-usd` as a matrix rail and name `--max-budget-usd 55` for D2, which
would have raised every spawn's ceiling elevenfold — removing the cost guard it
was written to install. The plan is corrected, not defended.

For this bank the rail should be **tightened**, not loosened: `--max-budget-usd 2`
matches the per-trial ceiling the planner already prints and bounds a runaway
trial. Anyone resuming under a "$50 rail" instruction should read it as a matrix
budget and translate accordingly.

---

## What this session changed in the repo

- `scenarios/e2-data-semantics/skill-vnext.toml` — the third arm. Model, effort,
  strategy, tool allow-list and limits copied verbatim from the other two; the
  only difference is which body is injected.
- `scenarios/e2-data-semantics/assets/skill-vnext.md` — the revised body,
  extracted by `git show <blob>` so it is LF and byte-exact, 16,511 bytes /
  303 lines, sha256 `68ae1837…`.
- `scenarios/e2-data-semantics/README.md` — provenance for the new asset, and the
  verification that `skill-current` is **byte-identical** to the commit the
  revision was branched from (`git show 07fea4f:<skill path>` diffs clean against
  the pinned asset). That is what makes `skill-current → skill-vnext` exactly the
  revision series and nothing else.

Existing arms were not touched. No ledger was written, because no trial ran.

## What the referee pass changed afterwards

Sixteen confirmed defects were fixed across both repos before any spend. The
ones that move this instrument, rather than only this document:

- **`skill-vnext.md` re-pinned** (`ecf03301…`, arm `config_hash` `ac01f476…`).
  The revision itself changed: an unsourced statistic cut, a severed cross-link
  restored, and the description's unauthorised fourth edit reverted.
- **The bank moved to `dataset_version = 2`.** Four contract fixtures narrated
  their own trap in prose — `refund_report.md` spelled out netted-to-zero versus
  no-rows and "Both report 0.00. Neither reports null"; `category_revenue.md`
  said joining on `product_id` alone "is a fan-out"; `monthly_volume.md` ruled
  `load_date` "not an event-time column"; `region_daily.md` said a differing
  representation "drops out of the join rather than failing loudly". Each of
  those hands the agent the answer, so the trap would have measured reading
  comprehension. Cut; the declarative semantics stayed. `fathom validate --strict`
  still reads 24/24.
- **`check_naive_refs` miscounted by one.** `benign-control` returned PASS
  through the control branch and was added to the discriminating total, so the
  tool printed "8 discriminate" for a bank with 7 traps, and two documents
  carried it forward. Controls now have their own column, and the tool's summary
  names what a PASS is: a self-consistency property with no agent behaviour
  observed.
- **The three-arm resume recipe** now runs the plan's mandatory `--repeats 1`
  pilot and its saturation gate before the 90-trial matrix, and states that the
  holdout step as written costs 30 trials where phase E funds 20.

None of it buys a trial. The verdict at the top is unchanged: **Unproven.**

## Resume steps

```sh
# 0. Operator, interactively: claude login    (nothing below works until this passes)
cd <fathom worktree>
uv run fathom smoke                                   # must read ALL PASS before spending

# 1. Prove both injected arms are armed on a live spawn
uv run fathom verify-arming --scenarios-dir scenarios/e2-data-semantics

# 2. PILOT FIRST -- 18 trials, not 90. This step is not optional (plan §9.5).
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 1 --dry-run                             # expect 18 trials
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 1 --max-budget-usd 2

# 3. SATURATION GATE (plan §9.7), read from the repeat-1 scorecard:
#    at least 2 of the 6 dev tasks must show the BARE arm failing its subtle
#    criterion. If fewer do, the bank ceilings -- STOP, do not spend the rest.
#    check_naive_refs cannot substitute: it observes no agent behaviour, and
#    validate.py's own docstring concedes neither catches a bank that is simply
#    too easy for every arm. This gate is the only instrument that can.
uv run fathom report e2-data-semantics

# 4. Only if the gate passes: the full matrix, resumable over the pilot's trials
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 5 --dry-run                             # expect 90 trials
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 5 --max-budget-usd 2                    # resumable; expected $25-40

# 5. Sealed holdout, deliberately and separately. Phase E funds 2 arms x 2 tasks
#    x 5 = 20 trials; --include-holdout with all three arms in the scenarios dir
#    runs 2 x 3 x 5 = 30. Use --limit, or run it with a two-arm scenarios dir.
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --include-holdout --repeats 5 --max-budget-usd 2

# 6. Render, then fill in the tables above from the scorecard
uv run fathom report e2-data-semantics
python tools/ledger_index.py --write     # re-stamp; the coverage test gates on it
```

Trigger side, in the craft-collection worktree:

```sh
python evals/harness/smoke.py
python evals/harness/run_triggers.py data-engineering-discipline --repeats 3   # 66 spawns
python evals/harness/holdout_check.py data-engineering-discipline --repeats 3  # 39 spawns
```

Read the holdout **once**, then record the row in
`evals/trigger/holdout/BASELINES.md` against the thresholds pre-registered there.
Do not tune the description against it afterwards.
