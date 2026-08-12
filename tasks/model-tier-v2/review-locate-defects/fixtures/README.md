# billing — review task

`billing/prorate.py` implements the six rules in `billing/RULES.md`, one function per
rule. Some of them do not.

## What a review produces

A file `REVIEW.md` at the root of the workspace, containing a `## Defects` section.
One line per defective function, in this exact shape:

    - <function_name> (<rule id>): <one sentence saying what is wrong>

For example, a defect in a function called `total` that breaks rule P9 would read:

    - total (P9): the sum ignores the discount.

List every function that does not implement its rule, and list nothing else — a
function named here that turns out to be correct is a false positive, and a review
that names everything is not a review.
