Users of the `book` package report that the two ways of computing the totals
disagree once a void is in the log. For
`[{"kind": "post", "id": "a", "amount": 100}, {"kind": "void", "id": "a"}]`,
`live.fold` reports `{"total": 0, "count": 1}` while `replay.replay` reports
`{"total": 0, "count": 0}`. Per the package README a voided entry counts for
nothing and the two paths must agree. Find and fix the bug so the package behaves
as documented. Preserve the existing public API, and keep the shipped test suite
passing.
