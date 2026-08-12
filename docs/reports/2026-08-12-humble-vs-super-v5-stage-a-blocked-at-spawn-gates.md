# humble-vs-super-v5 Stage A — not run: blocked at the spawn gates

**Date:** 2026-08-12. **Bank:** `humble-vs-super-v5`. **Branch:** `eval/humble-vs-super-merged`.
**Spend: $0.00. Trials run: 0. Ledger delta: none** — `ledger/humble-vs-super-v5.jsonl`
does not exist, and no lock was taken because nothing spawned a matrix.

## Outcome

Stage A was authorised and attempted this cycle. It **did not run**. The two real-spawn
gates that stand in front of any paid matrix — `fathom smoke` and `fathom verify-arming` —
both fail, on one shared root cause: the credential-only isolated spawn cannot
authenticate.

**Stage A is therefore UNMEASURED. It is not null, and it is not a verdict.** The
pre-registration in `tasks/humble-vs-super-v5/V5_NOTES.md` ("What Stage A is for",
re-registered 2026-08-12) is untouched by this document and still stands in full. Nothing
here licenses any reading of the cost axis, the quality axis, or either plugin.

## What the gates returned

`uv run fathom smoke` — run twice, byte-identical output both times:

```
[PASS] isolated config is credential-only            copied=['.credentials.json']
[FAIL] credential-only spawn authenticates & completes
       status=infrastructure turns=1
       result='Failed to authenticate: OAuth session expired and could not be refreshed'
[PASS] stream parsing detects activity               turns=1 tokens_in=0 tokens_out=0
[PASS] disallowed tool refused under default-deny     files_created=[] status=infrastructure
[FAIL] system-prompt injection reaches the model (treatment armed)
       flag_in_argv=True status=infrastructure canary_present=False
       result='Failed to authenticate: OAuth session expired and could not be refreshed'
[PASS] mount/available: canary skill listed in init event (treatment)   found=True  skills_count=16
[PASS] mount/available: canary skill absent without mount (control)     found=False skills_count=15
[FAIL] engine-boundary: non-bypass permission mode reaches the spawned CLI
       engine spawned no claude invocation (boundary not exercised)

SMOKE RESULT: SOME FAILED (5/8 checks)
```

`uv run fathom verify-arming --scenarios-dir scenarios/humble-vs-super-v5`:

```
  stack-humble:
    [FAIL] (probe) arming probe spawn completed
           probe spawn returned INFRASTRUCTURE: Failed to authenticate: OAuth session
           expired and could not be refreshed - arming is UNKNOWN, which is not the same as armed
  stack-super:
    [FAIL] (probe) arming probe spawn completed   (same message)

ARMING RESULT: SOME ARMS ARE NOT ARMED
```

## Why this is a stop and not a judgement call

Three separate rules land on the same answer, and none of them leaves discretion:

- **The smoke rule** is ALL PASS, or 7/8 with the *engine-boundary* check as the only
  failure. Of the three failures here, exactly one is that tolerated engine-boundary
  check; the other two are authentication. Strip the auth failures and this run would read
  7/8 engine-boundary-only — i.e. the auth pair is precisely and solely what converts a
  passing gate into a failing one.
- **`verify-arming` is a hard stop by the bank's own pre-registration**, which names
  `EXIT_UNARMED` as "the live gate" for `stack-super` and warns that a degraded contrast
  arm would "manufacture a null that looks like a measurement."
- **Every trial would have been an infrastructure error**, so the matrix would have bought
  zero measurement at any price.

## Two things worth recording about the instrument

**The arming checks that passed are init-event checks, and they pass without a model
call.** `mount/available` found the canary skill (16 skills vs 15 in the control) while the
spawn could not authenticate at all. Read carelessly, "the mount checks pass" would have
been false comfort — mounts were observed, but no arm was shown to *do* anything.
`verify-arming`'s wording is the correct one and is worth keeping: *arming is UNKNOWN,
which is not the same as armed.*

**The ledger could not have been poisoned, and this was verified rather than assumed.**
`src/fathom/cli.py` returns `EXIT_INFRASTRUCTURE` on the first infrastructure trial and
writes nothing for it:

```python
if trial_result.is_infrastructure:
    ...
    # Ledger is the resume checkpoint - no writes for this trial.
    return EXIT_INFRASTRUCTURE
```

So an attempted run would have halted at trial 1 with no ledger line and no consumed
resume cell. That is the designed behaviour working; it is not a reason to attempt the run.

## Gates that did pass (recorded, free)

| gate | result |
|---|---|
| `ruff format --check .` | 745 files already formatted |
| `ruff check .` | all checks passed |
| `pytest` | **642 passed, 1 skipped, 112 subtests** (the skip is an unrelated subskip in `test_verify_model_tier.py`: `feature-csv-coalesce` has no `original/` stash) |
| `fathom validate humble-vs-super-v5` | **5 pass, 0 fail, 0 warn, 10 unverifiable** (unchanged) |
| `tests/test_humble_super_v5_mounts.py` | **10 passed, none skipped** — the vendored `superpowers@6fd4507` tree is present on disk and matches its committed sha256 manifest |
| `fathom run ... --repeats 5 --dry-run` | **60 trials (0 already done), ceiling $120.00** |

The mounts test is the load-bearing one: the arming failure is an authentication problem,
**not** a missing-tree problem. The offline half of the arming guard is green, so no
re-vendoring is required.

## What restores the run

The expired OAuth session lives in the user-level CLI credentials that fathom copies into
each isolated spawn (`_CONFIG_COPY_ALLOWLIST = {".credentials.json"}`). The credential file
was deliberately not read or modified in the course of this cycle. Restoring the run is an
owner action:

1. Re-authenticate the Claude CLI so the credential file carries a live session.
2. `uv run fathom smoke` — require ALL PASS, or 7/8 with engine-boundary as the only failure.
3. `uv run fathom verify-arming --scenarios-dir scenarios/humble-vs-super-v5` — require ALL VERIFIED.
4. Then Stage A, unchanged and still pre-registered:

```sh
uv run fathom run humble-vs-super-v5 --scenarios-dir scenarios/humble-vs-super-v5 \
    --repeats 5 --limit 60 --max-budget-usd 1.75
uv run python scripts-humble-v5/analysis.py spend ledger/humble-vs-super-v5.jsonl
```

The resume key `(bank, dataset_version, task_id, config_hash, repeat)` makes Stage A
strictly additive whenever it is bought: the 60 planned trials are all still outstanding,
and nothing in this cycle consumed any of them.

## The framing that will apply when it does run

Stated here so it is not re-litigated later. Stage A is an **economy** measurement buying
one number: the paired-by-task per-trial cost gap between `stack-humble` and `stack-super`
on `claude-opus-5`. When published it must be labelled a **new measurement (a fork), not a
reproduction** — the vendored humblepowers is **0.9.1**, against the **0.3.1 / 0.4.0** the
older banks measured, and the base model moved from `claude-opus-4-8` to `claude-opus-5`
because 4.8 is no longer served. Treatment and base model moved together, so **v5's numbers
may not be differenced against v1–v4's**.

Gate 1 (unarmed `regression_test_present` under the retired `<= 10%` line) is registered as
**expected to fail**, is recorded as an observation, and licenses and blocks nothing. Gate 2
(correctness ceilings at 100%) remains the one result that still stops the run.
