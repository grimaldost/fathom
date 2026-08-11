# `e2-data-semantics` — the vNext proof attempt, and why it is still unbought

**2026-08-11.** Bank `e2-data-semantics`, arms `bare` / `skill-current` / `skill-vnext`.
Branch `eval/data-discipline`.

---

## Verdict in one line

**The three-arm matrix did not run. Zero trials, zero spend, no ledger.** Every
behavioural claim the revision makes about `data-engineering-discipline` stays
**Unproven** — not refuted, not supported. The trigger side is unbought for the
same reason. What this session did buy, for $0, is the rest of the instrument:
the third arm is authored, pinned and hash-distinct, the bank re-validates
24/24, all eight tasks re-confirm they discriminate, and the free half of the
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
| | **rowset_matches_known_good** | — | — | — | generalization |
| `watermark-frozen-partition` *(sealed)* | late_rows_loaded | — | — | — | |
| | **per_partition_cursor_advanced** | — | — | — | T1.5 adjacent freshness form |

**One reading note for whoever fills this in.** `oracle-capture` and
`benign-control` are the two tasks where only **1 of 2** criteria starts false on
the unmodified fixture. On `oracle-capture` that is by design and load-bearing:
`expected_values_unmodified` is a **preservation** criterion that starts true, so
an arm cannot earn it, only lose it. A pass on it in isolation is worthless —
the conjunction with `output_correct_on_subtle_case` is the whole measurement,
exactly as the plan specified. Read those two cells together or not at all.

### What is confirmed about the instrument (free, reproduced this session)

- `fathom validate e2-data-semantics --strict` → **24 pass, 0 fail, 0 warn, 0 unverifiable**.
- `tools/check_naive_refs.py e2-data-semantics --strict` → **8 discriminate, 0 fail**;
  `benign-control` correctly declares itself CONTROL rather than claiming to discriminate.
- All three arms resolve to **distinct `config_hash` values**, so the ledger cannot
  silently merge them.

## Economy by `config_hash`

Not measured. The keys are on record so a resumed run appends under exactly these
buckets, and so a later reader can tell whether a row belongs to this comparison:

| Arm | `config_hash` | Injected asset sha256 |
|---|---|---|
| `bare` | `46114dc029b19c6c8fd4bbaa3b51e4540785c1e086981f40ab6d7b5e492ed8e9` | — (no `[context]`) |
| `skill-current` | `86eb7710bc3c6718d0c0275de07cd275cafdc627dc4d8f598f22eea84cbbaf1a` | `00d05bb342b8350fc74c3bb8d58818a0f3a1922900f165b3967583d517928acf` |
| `skill-vnext` | `05b78326723c0e5d03d0462186e7b80f6850e42bb90b5e5861de70ae2c6c1368` | `68ae1837f248554fd7cb873b0b8a5d792950b28914fc84773bdd98ab4275620d` |

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
| Holdout | `evals/trigger/holdout/data-engineering-discipline.json` — 13 cases, **never run**, now carrying two seals at once (0.1.15 and 0.5.0) |
| Plan | 22 × 3 = **66 dev spawns**; holdout 13 × 3 = 39 |
| Pre-registered | dev recall on the tests-for-a-pipeline positive moves **0.33 → ≥ 0.80** with specificity **held at 1.00**; the holdout reads recall and specificity for the first time on this surface |

The description edit is a real, verified 1-word change in the eager tier
(223 → **224** words, 1424 → 1452 chars) — so the reseal obligation the baselines
file records is genuinely due, and the plan's sequencing constraint (one
description change buys one holdout run) is satisfied by the implementation as
landed. What is absent is the run.

Free evidence adjacent to the trigger claim: the router change is landed and
mechanically green. The three ambient nouns (`pipeline`, `dataset`,
`dashboard`/`warehouse`) moved out of the `min_hits: 1` group into their own
`min_hits: 2` group, a bounded `tests? for … pipeline` pattern was added to the
strong group, and `test_router.py` passes with its sealed-set floors intact.
That is a *dispatch-layer* result, not a description result — it does not
substitute for the trigger eval.

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
| T0.1a | `producer_census.py` + `parity_check.py --two-producer` ship and their checks can fail | `scripts/run_tests.py` → **52/52 passed**, including `test_producer_census.py`, `test_parity_check.py` |
| T0.2a | Parity numerics (`--null-mismatch` default-on, `--tol-col`, `--residual-zero`) ship with tests | same suite, `test_parity_check.py` |
| T0.3 | `mutate_check.py` proves each shipped check reddens on a seeded defect | same suite, `test_mutate_check.py` |
| T0.4 | `which_copy.py` ships with a unit test | same suite, `test_which_copy.py` — **no behavioural claim was made or bought** |
| T0.5 | Router: an ambient noun alone no longer routes the data skill | `test_router.py` green with sealed-set floors held |
| T0.6 | The three sentenced retirements executed | references **7 files / 28,759 words → 5 files / 16,522 words**; `glossary.md` and `community-practices.md` gone |
| T0.7 | Tool-general evidence modes re-homed, not deleted | `verification-before-completion/references/evidence-fabrication.md` added (+255 lines), cross-linked from that body |
| T1.8 | The cut is an enforced ceiling, not a one-off | body **2,736 → 2,323** words; `scripts/word_budget.json` ratcheted **2,736 → 2,380** in the same commit; 57 words of headroom |

A correction the plan's own arithmetic needs, confirmed here: the audit's "2,658
body vs 2,736 gate, so 78 words of headroom" compared two different metrics. On
the gate's metric the old body measured **exactly 2,736** — zero headroom. Any
additive edit would have tripped the ratchet, which is why every growth in this
wave had to displace first. The implementer's report states this correctly.

### Unproven — the instrument is ready, the run was not bought

| ID | Claim | Instrument | Status |
|---|---|---|---|
| T0.1b | The cross-producer **body line** changes behaviour | `two-producer-drift` / `both_producers_reconciled` | not run |
| T0.2b | The null-vs-zero rail changes behaviour | `null-vs-zero` / `null_semantics_preserved` | not run |
| T1.2 | The oracle-integrity rail as **prose** stops fixture editing | `oracle-capture`, conjunction of both criteria | not run |
| T1.3 | Grain / `DISTINCT`-as-fanout-repair content changes behaviour | `distinct-as-fanout-repair` / `measure_correct_after_fix` | not run |
| T1.4 | Time-semantics content changes behaviour | `time-window-misalignment` / `metric_correct_under_consistent_join` | not run |
| T2.1a | Description fix lifts the measured under-fire | craft trigger dev set, threshold 0.33 → ≥ 0.80 | not run |
| T2.1b | The schema-as-data ruling generalizes | craft holdout, 13 cases, double-sealed | not run |
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
| T1.6 | Checklist boxes → runnable invocations | Invoking a check is not workspace-observable unless it writes an artifact. Cost-only change |
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
says so: *"Per-spawn budget cap (overrides the adapter default of 5.0)"*. Passing
`--max-budget-usd 50` therefore **raises** each spawn's ceiling tenfold from the
$5 default; it does not bound the matrix at $50. Total spend is bounded by the
trial count (`--repeats`, `--limit`), by resumability, and by watching the
printed ceiling — not by this flag.

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

## Resume steps

```sh
# 0. Operator, interactively: claude login    (nothing below works until this passes)
cd <fathom worktree>
uv run fathom smoke                                   # must read ALL PASS before spending

# 1. Prove both injected arms are armed on a live spawn
uv run fathom verify-arming --scenarios-dir scenarios/e2-data-semantics

# 2. Plan, then run under the serialization lock
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 5 --dry-run                             # expect 90 trials
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 5 --max-budget-usd 2                    # resumable; expected $25-40

# 3. Sealed holdout, deliberately and separately
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --include-holdout --repeats 5 --max-budget-usd 2

# 4. Render, then fill in the tables above from the scorecard
uv run fathom report e2-data-semantics
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
