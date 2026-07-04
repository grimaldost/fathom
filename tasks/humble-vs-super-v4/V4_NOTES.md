# humble-vs-super-v4 — non-local root-cause retune

**Created:** 2026-06-16. **Why:** the v3 pilot (bare vs stack-super, 18 trials) showed
every correctness criterion ceilinged at 100% for `bare` — opus implements documented
contracts on self-contained functions without needing the discipline plugins. Only
`regression_test_present` discriminated (bare 0/9 vs stack-super 9/9). To make
**correctness** discriminate, v4 moves the bug **out of the symptom site**: an
innocent-looking shared helper is the real cause, and a second consumer + edge cases
defeat consumer-local band-aids. See `README.md` for the design rule.

## Hypothesis

A symptom-driven one-shot fixes the consumer where the error appears and fails the other
consumer; root-cause-tracing (a systematic-debugging discipline) fixes the shared helper
and passes both. If bare band-aids even *some* of the time, its correctness pass-rate
lands inside (0, 1) and v4 discriminates on correctness — the thing v3 could not.

**Risk (held honestly):** opus may trace to the helper reliably even when bare, in which
case v4 ceilings like v3. That outcome is a finding, not a failure — it bounds what these
disciplines can move on a highly capable base model.

## Pilot-gated plan

The pilot uses a subset scenarios dir (`scenarios/humble-vs-super-v4-pilot/` =
`bare.toml` + `stack-super.toml`, byte-identical to the full set → identical
`config_hash` → pilot trials resume into the full matrix).

```sh
uv run ruff format --check . && uv run ruff check . && uv run pytest   # gates
uv run fathom smoke                                                      # spawn isolation
# CALIBRATION PILOT: does bare band-aid (discriminate) or trace (ceiling)?
uv run fathom run humble-vs-super-v4 --scenarios-dir scenarios/humble-vs-super-v4-pilot \
    --repeats 4                                     # 2 arms x 2 tasks x 4 = 16 trials, ~$10
uv run fathom report humble-vs-super-v4
# POWERED MATRIX only if bare lands inside (0,1) on the correctness criteria.
uv run fathom run humble-vs-super-v4 --scenarios-dir scenarios/humble-vs-super-v4 --repeats <R>
```

If a re-pilot is needed after tweaking the SAME tasks, archive the prior v4 pilot ledger
(`ledger/humble-vs-super-v4.jsonl` → `ledger/archive/`) so the regenerated report stays
clean — the fathom "archive, re-run fresh" doctrine.

## Plugins

Mounted from v2's vendored tree (same content → identical `config_hash` for the shared
arms). Self-contain only if v4 graduates to a committed instrument.
