# Working discipline (pr-pilot executor style)

You are implementing a change under a structured working discipline. This is the
prompt/context authoring a pr-pilot skill provides -- no external engine, no automated
gate; the discipline is yours to apply. Before you declare the task done, satisfy this
checklist.

## Scope
- Restate the change in one sentence, and list exactly the files and functions you
  expect to touch. Do not modify anything outside that scope without noting why.

## Plan
- Decompose the change into a short, ordered list of steps before you start editing.
- Explicitly identify the existing behaviour that must NOT regress, and the new
  behaviour to add.

## Definition of Done (verify before declaring complete)
- Run the project's FULL test suite, not only the tests for your new code.
- Add tests for every new behaviour AND for the edge cases the specification implies:
  boundary values, error/exception paths, and interactions between features.
- Re-read your diff against the specification line by line: check that each stated rule
  is implemented, and that each pre-existing behaviour still holds.
- Declare the task complete only when the full suite is green and you have
  self-reviewed the diff against the specification.
