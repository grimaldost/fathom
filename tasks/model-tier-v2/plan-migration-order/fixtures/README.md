# schema — rollout planning task

`schema/migrations.py` holds the migrations. `schema/CONSTRAINTS.md` states the three
constraints an apply order has to satisfy.

## What a plan produces

A file `PLAN.md` at the root of the workspace with two sections.

    ## Order

    m5
    m1
    ...

One migration id per line, in the order they are to be applied, every migration
exactly once and nothing else on the line.

    ## Rationale

    - C1: ...
    - C2: ...
    - C3: ...

One line per constraint, each beginning with that constraint's id, saying how the
order above satisfies it.

No code changes: this task produces a plan, not a migration.
