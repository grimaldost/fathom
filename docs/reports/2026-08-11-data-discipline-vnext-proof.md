# `e2-data-semantics` — the vNext proof, half bought

**2026-08-11.** Bank `e2-data-semantics`, arms `bare` / `skill-current` / `skill-vnext`.
Branch `eval/data-discipline`.

---

## Verdict in one line

**The trigger side was bought in full and the pre-registered gate on it FAILED.
The three-arm matrix was not bought: zero trials, zero spend, no ledger.**

- **T2.1a failed its pre-registered gate — it is not merely unbought.** The
  description edit was written to move one query from 1/3 to 3/3. It measured
  **1/3 — no movement at all — on three valid runs with no errored positive
  runs**, which is the cleanest form that negative result can take.
  Dev-aggregate recall on the identical 22-query fixture went **0.94 → 0.82**
  (31/33 → 27/33) across the edit, with two queries regressing and none
  improving. *Failed the gate* is the exact claim: at three repeats even the
  maximum achievable movement would not have reached significance (p ≈ 0.4), so
  this does not refute the underlying hypothesis and licenses no revert.
- **Every behavioural claim that needs the matrix stays Unproven** — not refuted,
  not supported. That includes the one claim the plan pre-registered as
  *adjudicating* rather than reporting (T1.2), so **`oracle_guard.py` is not
  licensed to be built**; see the decision section.
- What was bought for $0 is the rest of the instrument, now with **live** proof
  it is armed rather than a static argument that it should be.

Per the operator's standing rule (*an improvement is claimed only when a test
proves it*), the revision does not get to describe itself as an improvement on
the strength of this report. On the one surface where a test ran, the test says
no.

---

## The blocker, corrected — it was never the credential

The previous version of this report named a dead OAuth refresh token as the
blocker. **That was true when it was written and is now resolved.** Credentials
were restored interactively by the operator, and every instrument that refused to
spend then, spends and passes now.

The matrix is unbought for an unrelated and much duller reason: **the shared
paid-run lock was held for the entire paid window by a sibling workflow**
(`verification-lift`, worktree `.wt-verification/fathom`, branch
`eval/verification-lift`) across three successive holders — pid 5395 from
20:19:48Z, pid 10397 from 22:47:19Z, pid 9547 from 00:14:27Z. The runner polled
at 5-minute granularity for ~2 h, then at 15 s, then ran a dedicated 25-minute
window at 5 s, and never found a gap. **The lock was not broken, stolen, or timed
out**, and the sibling worktree was never touched beyond a read-only `stat`/`wc`
of its ledger.

That is the correct behaviour and it is also why this report is half-empty. One
diagnostic is worth recording for whoever resumes: as of 01:41Z the holding pid
(9547) is **not alive** and the sibling's ledger has not grown since 20:56Z, so
the lock file is an orphan left by a process that died without releasing it —
the exact failure the *"delete it when done, including on failure"* half of the
protocol exists to prevent. Reclaiming an orphaned lock is the sibling
workflow's call or the operator's, not this chain's, so it was left in place.

### Pre-spend gates — all green, on live spawns

| Gate | Result |
|---|---|
| `fathom smoke` | **7/8**, the documented permitted state: only `engine-boundary` FAIL (needs a wired convoy engine, irrelevant to three `single-session` arms). `credential-only spawn authenticates & completes` **PASS** (`status=ok`); `system-prompt injection reaches the model` **PASS** (`flag_in_argv=True`, `canary_present=True`) |
| `fathom verify-arming --scenarios-dir scenarios/e2-data-semantics` | **ALL VERIFIED** on live spawns — `skill-current` verified at `body_bytes=19721`, `skill-vnext` verified at `body_bytes=16574`, `bare` is the control with nothing to verify |
| `fathom validate e2-data-semantics --strict` | **24 pass, 0 fail, 0 warn, 0 unverifiable** (reproduced again while writing this report) |
| `tools/check_naive_refs.py e2-data-semantics --strict` | **7 discriminate, 1 control, 0 fail, 0 unverifiable** (reproduced) |
| `fathom run … --repeats 1 --dry-run` / `--repeats 5 --dry-run` | **18** / **90** trials. The printed \$36 / \$180 are the planner's conservative \$2-per-trial ceiling, not an estimate; the comparable-based expectation for 90 stays \$25–40 |
| craft-collection `evals/harness/smoke.py` | **ALL PASS (5/5)** before either trigger spend |

The `verify-arming` reading the previous version defended in the abstract is now
concrete: the module distinguishes *unknown* from *armed* by construction, and
under live credentials it returns **armed**, with the injected body's byte count
as the witness.

**The saturation gate was never evaluated**, because the 18-trial pilot it reads
was never bought. The bank's discrimination headroom is therefore still unknown —
`check_naive_refs` cannot substitute for it, for the reason stated below.

---

## Three-arm per-criterion table

Every cell is **not measured**. The table is published in this shape so the
resumed run fills it in place rather than re-deriving what it should have
reported.

Bank `e2-data-semantics`, **`dataset_version = "2"`** (the referee pass bumped it;
the resume key is `(bank, dataset_version, task_id, config_hash, repeat)`, so any
row written against version 1 would not be resumable against this bank). Hard
criterion (the correctness gate) in **bold**; the other criterion on each row is
what the naive fix buys.

| Task | Criterion | `bare` | `skill-current` | `skill-vnext` | Claim it adjudicates |
|---|---|---|---|---|---|
| `two-producer-drift` | reconciliation_covers_all_periods | — | — | — | |
| | **both_producers_reconciled** | — | — | — | T0.1 body line |
| `oracle-capture` | output_correct_on_subtle_case | — | — | — | |
| | **CONJUNCTION of both** *(no `GATE` constant)* | — | — | — | T1.2 oracle rail |
| `distinct-as-fanout-repair` | total_revenue_correct | — | — | — | |
| | **measure_correct_after_fix** | — | — | — | T1.3 grain/fanout |
| `time-window-misalignment` | orders_in_window_correct | — | — | — | |
| | **metric_correct_under_consistent_join** | — | — | — | T1.4 time semantics |
| `null-vs-zero` | absent_regions_report_zero | — | — | — | |
| | **null_semantics_preserved** | — | — | — | T0.2 parity numerics |
| `benign-control` | helper_renamed | — | — | — | |
| | **CONJUNCTION of both** *(no `GATE` constant)* | — | — | — | interpretability + cost regression |
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

**And the verifiers already encode exactly that, which this report can now state
from source rather than from intent.** Six of the eight tasks declare a single
`GATE` constant and exit on it (`return 0 if result[GATE] else 1`) — the bold
criterion above is that constant, verbatim, in all six. The remaining two —
`oracle-capture` and `benign-control` — declare **no `GATE` at all** and exit on
`all(result.values())`, the conjunction of both criteria. So the corrected
adjudication rule for T1.2 is not a reinterpretation imposed on the instrument
after the fact; it is what the instrument's exit code has always computed. A
claim that "all eight GATE constants match the bold rows" is off by two: two
tasks have no such constant, which is why those two rows above now name the
conjunction instead of a criterion.

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

Not measured — `ledger/e2-data-semantics.jsonl` does not exist. The keys below
were **re-resolved from the repo while writing this report** (`load_scenario` →
`resolve_scenario` under `cli._DefaultResolver`, sha256 taken over the injected
file's bytes), so a resumed run appends under exactly these buckets and a later
reader can tell whether a row belongs to this comparison:

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

## Trigger side — **bought in full**

105 spawns, **$9.97**, `claude-sonnet-4-6`, `--repeats 3`, isolated
`CLAUDE_CONFIG_DIR` carrying the credential only (no `CLAUDE.md`, no
`settings.json`, so **no router hook is in the loop** — this surface measures the
description and nothing else). The dev fixture is byte-identical to the one that
produced the pre-edit baseline (`git log` shows it last touched at 0.1.8, before
this wave), and `evals/config.json` — model, repeats, tool lists — is likewise
untouched on this branch, so the pre/post comparison is same-fixture,
same-model, same-n.

### Dev pass — 66 spawns, $6.4445

| | measured | gate | |
|---|---|---|---|
| recall | **0.82** CI[0.66, 0.91] (27/33 runs) | ≥ 0.80 | **PASS** |
| recall excl. errored runs | **0.82** CI[0.66, 0.91] — identical | — | `errors_no_activation_positive = 0` |
| specificity | **1.00** CI[0.90, 1.00] (0 fires in 33 negative runs) | ≥ 0.90 | **PASS** |
| error runs | 13/66, of which 6 no-activation | — | all 6 landed on **negative** queries |

Every one of the 33 positive runs was valid. No positive query has a reduced
denominator, so nothing below is an infrastructure artefact. The 6 no-activation
errors sit on two negatives (*"Write a Typer CLI…"* 3/3, *"Set up pytest and
ruff…"* 3/3), where silence is the correct answer anyway — which makes
specificity **mildly optimistic on those two rows**: 9 of 11 negatives are fully
valid, 2 are entirely unassessable, and the positive side is untouched.

Per-query positives, all on 3 valid runs:

| k/3 | query |
|---|---|
| 3/3 | Migrate this Spark pipeline to the new warehouse |
| 3/3 | refactoring the transform that builds the orders fact table |
| **0/3** | The revenue numbers in the executive dashboard changed after my last merge |
| 3/3 | Design a data contract for the customer_events dataset |
| 3/3 | Add a churn_risk column to the users dimension table |
| 3/3 | Backfill six months of history into the sessions table |
| **1/3** | **Write tests for the billing aggregation pipeline so a bad change can't ship silently** ← the pre-registered query |
| 3/3 | Generate a PySpark job that rolls daily events up to monthly revenue |
| **2/3** | The orders pipeline ran green but the data didn't update |
| 3/3 | Our incremental load into customer_events isn't refreshing |
| 3/3 | The nightly job reports success but the extract the BI team reads hasn't changed |

All 11 negatives 0/3 — no over-fire anywhere.

### T2.1a — the pre-registered gate, and it FAILED

Pre-registered movement: **0.33 → ≥ 0.80** on *"Write tests for the billing
aggregation pipeline so a bad change can't ship silently"*, i.e. **1/3 → 3/3** at
`--repeats 3`. **Measured: 1/3 = 0.33 on three valid runs. Zero movement on the
exact query the edit was written for.** Fisher exact on 1/3 vs 1/3 is p = 1.0;
per the pre-registration this is a descriptive gate on valid runs, so no p-value
is reported for the gate itself and none should be.

The specificity half of the pre-registration — held at 1.00 — **is met**. The
recall half is not.

**The dev aggregate moved the wrong way too.** Pre-edit the same fixture measured
**recall 0.939 CI[0.80, 0.98]** (31/33); post-edit it measures **0.818
CI[0.66, 0.91]** (27/33). Reconstructing the difference: the target query is
unchanged at 1/3, *"The revenue numbers in the executive dashboard changed after
my last merge"* went **3/3 → 0/3**, and *"The orders pipeline ran green but the
data didn't update"* went **3/3 → 2/3**. Nothing improved.

**State the power before reading anything into that.** Fisher exact on 31/33 vs
27/33 is **two-sided p ≈ 0.26** — not significant, and the run-level denominator
flatters it anyway because three runs of one query are clustered, not three
independent trials. On the single regressed query, 3/3 → 0/3 is **p ≈ 0.10**.
And the ceiling was always low: the *maximum achievable* movement on the target
query, 1/3 → 3/3, is **p ≈ 0.4**, so this design could never have separated on
it. A significance claim on one query needs ≥ 9 repeats (9/9 vs 3/9 → two-sided
p ≈ 0.009), which is a different purchase.

So: the edit **failed its own descriptive gate cleanly**, and is **associated
with** a dev-aggregate decline that this n cannot establish. Those are two
different strengths of statement and the second must not borrow the first's.

### Sealed holdout — 39 spawns, $3.525, the single sanctioned read

The 223 → 243-word reseal obligation is **discharged**. The harness's pooled
output — recall 0.62 CI[0.43, 0.79] on 8 positives, specificity 1.00
CI[0.80, 1.00] on 5 near-misses, 1/39 error runs (no `recall excl. err` line was
printed, which by the harness's own control flow at `holdout_check.py:162` means
`errors_no_activation_positive = 0`, so all 24 positive runs were valid and the
single errored run fell on a negative) — **is the number BASELINES.md forbids
reading**, because it mixes 7 spent-dev cases with 6 sealed ones. The harness
also auto-printed *"dev recall 0.82 (CI lo 0.52) vs held-out 0.62 → within dev
CI: generalizes"*; that line is pooled over all 13 cases and is **not** the
finding. The two strata:

**Stratum A — genuinely unseen (6 cases).** Unseen recall **9/12 runs = 0.75**
CI[0.47, 0.91] (query-level 3/4); unseen specificity **6/6 = 1.00** CI[0.61, 1.00].

| result | seal | case |
|---|---|---|
| 3/3 FIRE | 0.1.15 | lexical guard — DataHub metadata emitter serving payload + catalog tool |
| 3/3 FIRE | 0.1.15 | **intent paraphrase** — a service writes a JSON doc another team's dashboard ingests. *The one row on this surface that tests generalization, and it passes* |
| 0/3 silent (correct) | 0.1.15 | over-fire guard — CLI `--help` banner text |
| **0/3 MISS** | 0.5.0 | schema-as-data positive — hand-written YAML a generator turns into `CREATE TABLE` |
| 3/3 FIRE | 0.5.0 | schema-as-data positive — hand-authored lineage YAML a separate ingestion job reads |
| 0/3 silent (correct) | 0.5.0 | schema-as-data negative — diagram source JSON only rendered to SVG |

**Stratum B — 7 spent-dev cases re-used, carrying no surprise.** Recall **6/12
runs = 0.50** CI[0.25, 0.75] (query-level 2/4); specificity **9/9 = 1.00**.

| result | case |
|---|---|
| **0/3 MISS** | Why isn't the warehouse fact table picking up new rows… (freshness) |
| **0/3 MISS** | The BI report's 'last refreshed' date hasn't moved since Tuesday (freshness) |
| 3/3 FIRE | porting the attribution pipeline to BigQuery, totals must match |
| 3/3 FIRE | Add a region column to the accounts dataset two finance models consume |
| 0/3 silent ×3 (correct) | browser stale CSS; npm lockfile; parquet scratch notebook |

**Two readings the strata buy that the pooled number hides.** First, the 0.1.15
intent paraphrase — the case the collection's own pattern predicted would miss,
and the only genuine generalization row here — fires 3/3. Second, the
schema-as-data ruling is **decidable but not uniformly applied**: it fires on one
of its two positives and correctly withholds on its negative, at n = 1 query per
outcome. And both freshness-form positives in stratum B missed at full 3-run
denominators, which is worth the next reader's attention precisely because the
plan **deliberately did not** collapse the four near-synonym freshness phrasings.

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

**With the read in hand, that itemisation earns its keep.** (a) was the change
aimed at the target query and (a) did not move it. (b) is the change the sealed
0.5.0 cases test, and it lands one of two positives with a correct negative. So
the mixture problem the revert was worried about does not arise here: the two
edits are separable *by which set reads them*, and each is separately
disappointing — (a) at zero movement, (b) at half its positives.

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

Four buckets. **Proven** means a test in this repo or in craft-collection was
executed and passed. **Measured and failed** means a paid run happened and the
pre-registered gate was not met. **Unproven** means the instrument exists, is
validated, and was not run. **Not measurable by this bank** means the plan itself
tagged the item unprovable, and this report agrees — those must never migrate to
"proven" by silence.

### Measured and failed (paid, pre-registered, read once)

| ID | Claim | Gate | Measured | Verdict |
|---|---|---|---|---|
| **T2.1a** | The description fix lifts the measured under-fire | 1/3 → **3/3** on *"Write tests for the billing aggregation pipeline…"*, 3 repeats, descriptive, specificity held at 1.00 | **1/3**, three valid runs, `errors_no_activation_positive = 0`; specificity **1.00** | **FAILED on recall, met on specificity.** No movement whatsoever on the query the edit was written for, at a full denominator. This is the strongest available form of the negative — not an infrastructure artefact, not a reduced-n fluke |
| **T2.1b** | The schema-as-data ruling is self-consistent and decidable *(relabelled from "generalizes")* | the 3 cases sealed at 0.5.0 | 1 of 2 positives fires 3/3, the other misses 0/3; the negative correctly stays silent 0/3 | **PARTIAL.** Decidable — the negative is withheld and one positive fires cleanly — but not uniformly applied. n = 1 query per outcome; this cannot be pushed further without a wider sealed set |
| — | Generalization of the 0.1.15 emitter category | the 0.1.15 intent paraphrase, the one genuine generalization row | **3/3 FIRE** | **PASSED**, against the collection's own prediction that unseen intent paraphrases miss (toolkit-awareness 0.00, choosing-tools 0.00, python-engineering 0.00). n = 1 query |
| — | Dev specificity is not bought with over-fire | ≥ 0.90 | **1.00**, zero fires in 33 negative runs (2 of 11 negatives unassessable — all 6 no-activation errors landed there) | **PASSED**, with the caveat named |
| — | Dev recall gate | ≥ 0.80 | **0.82** CI[0.66, 0.91] | **PASSED** as a gate — while being **lower** than the 0.939 the same fixture measured before the edit |

**The one thing this bucket does not license.** The dev-aggregate decline
(0.939 → 0.818) and the two regressed queries are **descriptive**. Fisher exact
on 31/33 vs 27/33 gives p ≈ 0.26, the run-level denominator is clustered by
query, and the single worst regression (3/3 → 0/3) sits at p ≈ 0.10. Per the
operator's rule, **no retirement or reversal conclusion may be drawn from a
measurement this underpowered.** What is licensed: T2.1a's own pre-registered
gate is failed, because that gate was defined descriptively on valid runs and
the runs are valid. What is not licensed: "the description edit made the skill
worse", or any decision to revert it, on this n.

### Proven (free tests, reproduced independently)

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
| ~~T2.1a~~ | — | — | **moved to Measured and failed** |
| ~~T2.1b~~ | — | — | **moved to Measured and failed** (partial) |
| — | vNext ≥ current, and vNext > bare, in aggregate | three-arm matrix | not run |
| — | The cut items are non-inferior (no cost regression) | `benign-control` + economy join | not run |
| — | **The bank discriminates at all** (§9.7 saturation gate: `bare` fails its subtle criterion on ≥ 2 of the 5 dev traps, benign-control excluded as the declared control) | 18-trial pilot | **not run — and this one gates the other seven.** Until it reads, the bank's discrimination headroom is unknown and every row above is unproven for two independent reasons: the run did not happen, *and* nobody knows whether the run could have separated |

The single most consequential of these is **T1.2**, because the plan
pre-registered it as the one place the bank *adjudicates* rather than reports: if
`bare` edits the sealed fixture at a measurable rate and `skill-vnext` does not,
the prose is proven and `oracle_guard.py` must **not** be built; if **both** arms
edit it, the prose failed and the script is the pre-registered escalation. That
decision is still open, and no amount of static verification can close it.

### The T1.2 adjudication — `oracle_guard.py` is NOT licensed

The §9.7 decision table gives three rows for `oracle-capture`, and **all three
require trials that do not exist**:

| Pre-registered observation | Consequence | Observed |
|---|---|---|
| `bare` repairs the transform **and** edits the fixture at a measurable rate; vNext repairs **and** leaves it intact | rail proven as prose; **do not build** `oracle_guard.py` | — |
| **Both** arms repair **and** edit the fixture | prose failed; **build** `oracle_guard.py` with unit tests, and the rail's wording goes back for a rewrite | — |
| An arm scores `expected_values_unmodified` **without** `output_correct_on_subtle_case` | task-completion failure; count it neither way | — |

**Decision executed: do not build `oracle_guard.py`.** Not because the prose was
proven — it was not — but because the trigger condition for the escalation
(*both* arms editing the fixture) was never observed, and a pre-registered
escalation fires on its registered antecedent or not at all. Building it now
would be an unregistered addition justified by zero trials, in a wave whose whole
discipline is that additions displace and claims wait for tests. The escalation
stays armed and unfired; the resumed pilot can trip it in 18 trials.

The corrected conjunction reading is what the resumed run must adjudicate on, and
— as recorded above — it is already what `oracle-capture/verify.py` computes,
since that task has no `GATE` constant and exits on `all(result.values())`.

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
  extracted by `git show <blob>` so it is LF and byte-exact. As first pinned:
  16,511 bytes, sha256 `68ae1837…` — **superseded and never run.** The referee
  pass re-pinned it; the asset now on disk is **16,574 bytes**, sha256
  `ecf03301…`, and `verify-arming` reported exactly that byte count back from a
  live spawn. Aggregate on `config_hash` `ac01f476…`, never on `05b78326…`, or
  the vNext arm reads as absent.
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

None of it buys a trial. The matrix verdict is unchanged: **Unproven.**

## What the paid window bought, and what it cost

| | spawns / trials | spend |
|---|---:|---:|
| craft trigger dev pass | 66 | $6.4445 |
| craft sealed holdout (single sanctioned read) | 39 | $3.525 |
| fathom `e2-data-semantics` matrix | **0** | **$0** |
| **total** | **105** | **$9.97** |

Against dd-plan §9.6's $150 ceiling, phase B was budgeted $12 and came in at
$9.97; phases C/D/E ($93 of committed budget) are entirely unspent. Process
hygiene at both ends: no `fathom.exe`, no orphaned harness spawns, both worktrees
clean, and no ledger appended — so no `ledger_index` re-stamp was owed and
`test_ledger_coverage` stays green. Re-stamping it while writing this report
produced no diff, which is the confirmation.

## Resume steps

The pre-spend gates below have all been run and passed already; re-run them
anyway at resume, because a resume is a new session.

```sh
# 0. Take the paid-run lock. As of this writing it is an ORPHAN: the file names
#    verification-lift pid 9547, and that process is not alive. Confirm the
#    holder is dead before reclaiming, and reclaiming is the operator's call.
cd <fathom worktree>
uv run fathom smoke      # 7/8 with ONLY engine-boundary FAIL is the permitted
                         # state for these three single-session arms. ANY
                         # authentication failure means stop, no spend.

# 1. Prove both injected arms are armed on a live spawn
uv run fathom verify-arming --scenarios-dir scenarios/e2-data-semantics

# 2. PILOT FIRST -- 18 trials, not 90. This step is not optional (plan §9.5).
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 1 --dry-run                             # expect 18 trials
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 1 --max-budget-usd 2

# 3. SATURATION GATE (plan §9.7), read from the repeat-1 scorecard:
#    at least 2 of the FIVE dev TRAPS must show the BARE arm failing its subtle
#    criterion. Scoring, exactly:
#      - benign-control is EXCLUDED -- it is the declared control, not a trap,
#        so a bare pass on it is the expected result and cannot count toward
#        discrimination (this is the same off-by-one that made check_naive_refs
#        print "8 discriminate" for a bank with 7 traps).
#      - oracle-capture is scored as the CONJUNCTION
#        (output_correct_on_subtle_case AND expected_values_unmodified), because
#        expected_values_unmodified is a preservation criterion that starts TRUE
#        and is therefore passed by a do-nothing trial. verify.py already exits
#        on all(result.values()) for this task -- there is no GATE constant.
#    If fewer than 2 traps discriminate, the bank ceilings -- STOP, do not spend
#    the rest. check_naive_refs cannot substitute: it observes no agent
#    behaviour, and validate.py's own docstring concedes neither catches a bank
#    that is simply too easy for every arm. This gate is the only instrument
#    that can, and it has NEVER BEEN EVALUATED.
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

**A flag the resume must decide rather than discover.** Step 5 as written runs
2 tasks × 3 arms × 5 = **30** trials where phase E funds 20. Dropping `bare`
saves ~$3.50 and leaves the holdout without the report's pairwise anchor. Running
all 30 puts the whole resume at roughly 120 trials / $32–53, inside the plan's
committed envelope and inside a "$60 stop" rule. Given the operator's rule
against conclusions from underpowered measurements, the argument runs toward more
data, not less — but it is a decision, not a default.

Trigger side, in the craft-collection worktree — **already bought; do not re-run
the holdout.**

```sh
python evals/harness/smoke.py                                                  # DONE, 5/5
python evals/harness/run_triggers.py data-engineering-discipline --repeats 3   # DONE, 66 spawns
python evals/harness/holdout_check.py data-engineering-discipline --repeats 3  # DONE, 39 spawns -- SEAL SPENT
```

The holdout was read **once** and the row is recorded in
`evals/trigger/holdout/BASELINES.md`. That seal is now spent: tuning the
description against these numbers would convert a holdout into a dev set (the
2026-06-10 spent-holdout precedent). Any further description work on this skill
needs a fresh seal, and re-running the holdout to repair an infrastructure error
is the only sanctioned re-read.
