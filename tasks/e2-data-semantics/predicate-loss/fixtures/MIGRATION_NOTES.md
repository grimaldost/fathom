# Migration notes — active-accounts extract

The retiring platform's nightly query is preserved verbatim in
`legacy/accounts.sql`. `active_accounts.py` is the port.

**Cutover criterion: bug-for-bug parity.** The ported extract returns the same
rows as the legacy query for the same `as_of`. Improvements, cleanups and
"obviously wrong" predicates are out of scope for the port; anything we choose to
change is recorded here with a sign-off before it ships.

Divergences agreed so far: none.
