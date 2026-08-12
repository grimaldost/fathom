# model-tier-v2 — admission screen arms (stage 0)

Two arms, `haiku` (weak) and `opus5` (strong): the widest contrast on the ladder, and
the cheapest decisive read on the question the design's Part B asks before any matrix
is bought — **does this bank have headroom, or does the weak tier already saturate it?**

The arm files here are copies of `../model-tier-v2/haiku.toml` and `opus5.toml`. What
matters is not that the bytes match but that the RESOLVED configuration does: `name`,
`model`, `strategy`, `effort`, tools and limits all enter `config_hash`, and the resume
key is `(bank, dataset_version, task_id, config_hash, repeat)`. Identical resolution
means a screen trial and a matrix trial for the same `(task, repeat)` are the SAME
ledger bucket, so the screen is not an extra purchase — the matrix resumes over it and
pays only for what the screen did not already run.

`tests/test_bank_model_tier_v2.py::TestScreenArms` asserts that identity by resolving
both directories and comparing hashes, so an edit to one that is not mirrored in the
other fails the suite instead of silently forking the ledger and re-paying.

## What the screen buys

```sh
uv run fathom run model-tier-v2 \
  --scenarios-dir scenarios/model-tier-v2-screen \
  --tasks feature-ndjson-merge,fix-strip-unicode,fix-tz-window,fix-decimal-round \
  --repeats 5 --max-budget-usd 2 --dry-run
```

40 trials, printed ceiling $80. The four tasks are the mid band — the four rungs the
whole boundary-placement question rests on, since it is exactly the claim "the weak
tier fails these and the mid tier passes them" that places the 25 and 55 cuts.

**Decision rule, fixed before the spend.** For each of the four tasks: if `haiku`
passes every hard criterion on all 5 repeats, that task is SATURATED — it carries no
information about where a tier boundary sits, and it is reshaped or dropped from the
run set before the mid arm is paid for. If all four saturate, the mid band is empty
and the matrix is not bought at all: nothing about tier boundaries can follow from a
bank whose mid rungs a weak model clears.

Note what the screen cannot do: `haiku` failing is consistent both with "the task has
real headroom" and with "the task is impossible for every tier". The floor reading
comes from the `opus5` arm in the same screen — a task neither arm passes is at the
floor, not at a boundary.
