# Ledger index — the stamp every verdict is read against

**Generated. Do not hand-edit.** Re-render with `python -m fathom.ledgerindex --write` from
the data root; `fathom reconcile` fails while this file and `ledger/` disagree.

One row per committed ledger (archived ledgers under `ledger/archive/` are excluded).
`n by arm` counts trial rows with `status == "completed"` only — the same rule the resume
key and every scorecard use, so an errored trial is never a measured failure. A document
that quotes a per-arm n, a pooled control total or a p-value for one of these banks is
quoting *this* row; if it disagrees, the document is stale.

| Bank | ledger sha256 | n by arm (completed) | trial rows | run rows |
|---|---|---|---|---|
| `example` | `9eb04d629563b627641bc91c647fc37ddc5d309ae0fab980162c8d2ce4879b22` | bare:2, nudge:2, nudge-draft:1 | 5 | 5 |
