# cfg

Three-way merge for configuration maps.

Given a common `base` and two edited copies, `ours` and `theirs`, a merge decides
each key by the same four rules:

| what happened to the key                              | result                        |
|-------------------------------------------------------|-------------------------------|
| changed on one side only                              | that side's value             |
| changed on **both** sides to the **same** value       | that agreed value             |
| changed on both sides to **different** values         | a `Conflict(base, ours, theirs)` |
| **deleted** on one side, untouched on the other       | absent from the result        |

Deleting on both sides is a deletion, not a conflict. Deleting on one side while the
other side changes the value is a conflict, like any other disagreement.

Two entry points apply those rules:

- `merge.merge(base, ours, theirs)` — flat maps.
- `nested.merge_tree(base, ours, theirs)` — the same rules, recursing into keys whose
  value is a map on all three sides.

`merge.MISSING` is the internal marker for "this key is not in that map". It is an
implementation detail: it must never appear in a merge result.

Run the tests: `python -m unittest discover -s tests -t .`
