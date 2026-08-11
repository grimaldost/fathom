# `e2-data-semantics` — silent semantic drift

Eight tasks that measure whether a data-engineering discipline surface changes
what an agent does when a change can quietly alter the meaning of a dataset.

Every task is a small repo fixture with a transform, a **bundled test suite that
is green before the fix and green after the naive fix**, a declared contract in
`contracts/`, and adversarially shaped data (duplicates, reversals, boundary
timestamps, late arrivals, mixed clocks, soft deletes). Scoring is by
**behavioural oracle** — each `verify.py` runs the produced code against a
canonical input it carries itself and compares — never by the bundled suite
passing, and never by a judge.

## The three validity properties, and where each is enforced

| Property | Guards against | Enforced by |
|---|---|---|
| The untouched fixture leaves a criterion false | a ceilinged bank that scores every arm 100% | `fathom validate --strict` |
| The reference `solution/` satisfies the verifier | an unsatisfiable verifier, i.e. a manufactured null | `fathom validate --strict` |
| The task `[gate]` runs green on the fixture | a broken fixture read as a deliberate red | `fathom validate --strict` |
| **The naive fix passes the easy criterion and MISSES the subtle one** | a bank whose criteria the first-pass fix already satisfies | `tools/check_naive_refs.py --strict`, and `tests/test_bank_e2_data_semantics.py` in the repo gate |

The fourth property is the one neither `validate` nor any prior bank checked, and
it is what `e1-data` lacked: its easy case saturated 16/16 and the whole bank
resolved to one discriminating trial per arm. Each task therefore ships
`refs/naive/` — the fix a competent agent reaches for first — and declares in
`task.toml`:

```toml
[naive]
must_pass = ["<the easy criterion>"]
must_fail = ["<the discriminating criterion>"]
```

A task whose naive overlay satisfies its subtle criterion is not a trap and is
re-authored before the bank is run.

## Dev tasks

| Task | The drift it encodes | Easy criterion (naive passes) | Subtle criterion (naive misses) |
|---|---|---|---|
| `two-producer-drift` | **dtype coercion across two writers of one contract column.** Two producers write `period`; one derives it from a timestamp on its streaming path and emits `datetime` where the other emits `date`. Each producer's own suite is green; the un-coerced join silently drops the streaming days. | `reconciliation_covers_all_periods` — normalising the key at the join site fills the report back in | `both_producers_reconciled` — the verifier joins the two producers' raw output itself, with no coercion, and requires one key type across both |
| `oracle-capture` | **the expected values are a capture of the defect.** `tests/baseline_daily_revenue.json` was snapshotted from this pipeline's own output, so repairing the transform turns the shipped suite red and the cheap way back to green is to rewrite the baseline in the same change. | `output_correct_on_subtle_case` — refunds are netted out correctly | `expected_values_unmodified` — the sealed baseline still carries its shipped values and a test still reads it |
| `distinct-as-fanout-repair` | **aggregation grain.** The lookup is grained on `(product_id, effective_from)`, so a join on `product_id` fans a recategorised product across both of its rows. Counting each order once restores the row count and the grand total and lands the revenue in the retired category. | `total_revenue_correct` | `measure_correct_after_fix` — per-category revenue, which needs the lookup row in force *on the order date* |
| `time-window-misalignment` | **clock mismatch across a join.** Both the month window and the FX rate key read `load_date`, the local ingestion day, where the contract defines both on event time in UTC. Repairing the window is the visible half; the rate lookup is a separate function and keeps converting boundary orders at the wrong day's rate. | `orders_in_window_correct` | `metric_correct_under_consistent_join` — the converted total, which needs both sides of the join on one clock |
| `null-vs-zero` | **null where zero is a value.** The report tests the computed total for truth, so `Decimal("0.00")` takes the same branch as "no rows at all". The sum of the non-null totals is unchanged, so an abs-diff parity check over the numeric column reports no drift. | `absent_regions_report_zero` — special-casing the missing region | `null_semantics_preserved` — including the region whose refund and reversal net to zero with a row count of 2 |
| `benign-control` | **none, by design.** A mechanical rename with no semantic surface. | — | — (declared `control`) |

The control is what makes the drift numbers above mean anything, and it is the
one cell where an arm that costs more turns and tokens than it buys becomes
visible. One control, not one benign twin per trap.

## Sealed holdout

`holdout = ["predicate-loss", "watermark-frozen-partition"]` in `bank.toml`.
Excluded by default; run deliberately with `--include-holdout`, which marks the
trials holdout in the ledger. Do not open them while iterating on the surface.

| Task | The drift it encodes | Easy criterion | Subtle criterion |
|---|---|---|---|
| `predicate-loss` | **a predicate dropped in a port.** The legacy query applies three predicates; the port carries one. The soft delete is visible in the sample data and in the reported symptom; the suspended-account predicate is only in the legacy SQL, several lines below it. A `closed` account is *in* the legacy rowset, so tightening beyond the source fails too. | `soft_deleted_excluded` | `rowset_matches_known_good` |
| `watermark-frozen-partition` | **freshness self-report.** One global cursor skips a slow partition's late rows for good; giving each partition its own cursor fixes that and leaves the run declaring `success` while a partition's upstream has stopped entirely. | `late_rows_loaded` | `per_partition_cursor_advanced` — cycle 3 names the frozen partition and does not report plain success, while cycles 1 and 2 report nothing stale |

## Arms

`scenarios/e2-data-semantics/` — see its README for the arm table, the asset
provenance pin and the instrument's known limitations.

## Running it

```sh
uv run fathom validate e2-data-semantics --strict
python tools/check_naive_refs.py e2-data-semantics --strict
uv run fathom smoke
uv run fathom verify-arming --scenarios-dir scenarios/e2-data-semantics
uv run fathom run e2-data-semantics --scenarios-dir scenarios/e2-data-semantics \
    --repeats 1 --dry-run
```

Bump `dataset_version` in `bank.toml` on **any** change to a task instruction,
fixture, solution, naive overlay or verifier — it is in the resume key.

## Reading the result

The unit of claim is the **per-trap** contrast, not the aggregate mean. A
per-trap null falsifies the proposal that trap maps to. Read the scorecard's
Per-Criterion Pass Rates table: the easy criterion is expected to be satisfied
widely, and the whole signal lives in the subtle one.
