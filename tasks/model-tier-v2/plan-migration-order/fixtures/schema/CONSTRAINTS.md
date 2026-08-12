# Rollout constraints

An apply order is valid when all three constraints hold. Every migration in
`schema/migrations.py` is applied exactly once; nothing is skipped and nothing is
split.

- **C1 dependencies** — a migration is applied after every migration in its
  `depends_on`.
- **C3 additions before backfills** — every migration whose `kind` is `backfill`
  comes after **every** migration whose `kind` is `add`, whether or not it depends on
  it. A backfill reads rows that any pending addition may still reshape, so a
  dependency-only order is not enough. The order therefore has two phases: all the
  additions, then all the backfills.
- **C2 one table at a time, within each phase** — read the additions on their own and
  the backfills on their own. Within each of those two runs, the migrations touching a
  given `table` are **contiguous**: once a phase leaves a table it does not come back
  to it. C2 is scoped to a phase because C3 already splits every table's work in two;
  asking for contiguity across the whole order as well would have no solution at all,
  and a constraint set with no solution measures nothing.

C1 alone has many solutions and most of them break C2 or C3. C3 is the constraint a
dependency sort will not find on its own, and C2 is the one that is easy to satisfy by
accident and easy to lose when C3 is applied carelessly.
