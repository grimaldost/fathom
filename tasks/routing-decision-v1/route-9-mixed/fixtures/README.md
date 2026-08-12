# Routing decision

This workspace holds one or more **task briefs** under `briefs/`. Each brief is the
instruction text a coding agent would be given if that task were dispatched.

Your job is not to do the tasks. Your job is to decide, for each brief, **which model
tier that task should be dispatched to**.

Three tiers are available, cheapest first:

| tier | character |
|---|---|
| `weak` | the cheapest model |
| `mid` | the mid-priced model |
| `strong` | the most expensive model |

## What to write

Write `routing.json` at the root of this workspace:

```json
{
  "routes": {
    "<brief-id>": "weak|mid|strong"
  }
}
```

One entry per brief, keyed by the brief's id (the filename under `briefs/` without
its `.md` suffix). Every brief must appear exactly once, and every value must be one
of `weak`, `mid`, `strong`.

Write nothing else. Do not modify the briefs.
