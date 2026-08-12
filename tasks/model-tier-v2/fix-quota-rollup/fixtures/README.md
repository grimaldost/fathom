# quota

Per-team usage quotas.

## The rollup invariant

A `Team` keeps a **rollup** of its members' usage in `Team.used`. The invariant the
whole package rests on:

> `team.used` always equals `sum(member.used for member in team.members)`.

`Team.add_usage(member, amount)` is the **only supported mutation point**: it is the
one place that charges a member and keeps the rollup in step. `Team.recompute()`
rebuilds the rollup from the members if it ever needs restoring.

Three readers depend on the rollup being current, and read it rather than
recomputing it, because recomputing on every read does not scale:

- `report.team_usage(team)` — how much of the quota is in use.
- `Team.remaining()` — how much is left.
- `limits.check(team)` — raises `QuotaExceeded` when the team is over its limit.

## Recording usage

- `usage.record(member, amount)` — the public entry point callers use to charge
  usage as it happens. A negative amount is a refund.

Run the tests: `python -m unittest discover -s tests -t .`
