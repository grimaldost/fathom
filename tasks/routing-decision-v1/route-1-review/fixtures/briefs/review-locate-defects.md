`billing/prorate.py` is meant to implement the six rules in `billing/RULES.md`, one
function per rule. Some of the functions do not.

Review the module against the rules and write `REVIEW.md` at the root of the
workspace, in the shape `README.md` specifies: a `## Defects` section with one line
per defective function, reading

  - <function_name> (<rule id>): <one sentence saying what is wrong>

Name every function that does not implement its rule, and name nothing else — a
correct function listed as a defect is a false positive, and a review that names
everything has decided nothing.

Change no code. `billing/prorate.py` must be byte-identical when you are done, and
the shipped test suite must still pass.
