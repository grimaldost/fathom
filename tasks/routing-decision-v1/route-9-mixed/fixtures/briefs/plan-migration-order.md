`schema/migrations.py` holds nine migrations with their tables, kinds and
dependencies. `schema/CONSTRAINTS.md` states the three constraints C1, C2 and C3 that
an apply order has to satisfy — all of them, not just the dependencies.

Write `PLAN.md` at the root of the workspace in the shape `README.md` specifies: an
`## Order` section listing every migration id exactly once, one per line, in the order
they are to be applied; and a `## Rationale` section with one line per constraint,
each beginning with that constraint's id, saying how your order satisfies it.

Change no code. `schema/migrations.py` must be byte-identical when you are done, and
the shipped test suite must still pass.
