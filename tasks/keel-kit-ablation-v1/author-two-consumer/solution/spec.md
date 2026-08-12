# Spec — per-region counts in the tinyetl run summary

- **Date:** 2026-08-11
- **Status:** draft
- **Kit:** 0.14.0
- **Kind:** series
- **Audience:** the implementing engineer, and the owners of the two jobs that read the summary
- **Output artifact(s):** `tinyetl/load.py`, `tinyetl/cli.py`, `tests/test_summary.py`

## Context

The run summary is built in one place — `tinyetl/load.py:26` `def summary` — and printed at
`tinyetl/cli.py:33` `summary(`. Two jobs read it: `reporting-daily` charts the daily volume and
`alerting-hourly` pages when the volume drops to zero. Both read the same mapping, so a change to
it is a contract change for both, which is why `docs/adr/0002-orders-are-append-only.md` treats
the emitted shape as a versioned contract rather than an implementation detail.

## Goal

Report how many rows were written per region alongside the existing total, without changing the
meaning or the name of the total either reader depends on.

## Gate commands

- `python -m unittest discover -s tests -t .`
- `python -m tinyetl.cli --config run.json`

## Non-goals

Neither reader is modified in this wave; the record shape on disk is untouched; no new region
vocabulary is introduced.

## Invariants touched

- **An emitted field never changes meaning under its own name** — `row_count` keeps meaning the
  total rows written. Recorded in `docs/adr/0002-orders-are-append-only.md`.
- **Every out-of-wave consumer of the summary is named before the shape moves** — the two jobs
  above are the complete list, and each is listed in the PR that changes the shape.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| field-never-changes-meaning | enforced | `tests/test_summary.py` pins `row_count` to the total written |
| consumers-named-before-shape-moves | review-only | no gate today; the reviewer checks the file list |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| per-region counts | `tinyetl/load.py` |
| summary contract | `tinyetl/load.py` |
| summary emission | `tinyetl/cli.py` |
| consumer migration notes | `docs/adr/0003-summary-adds-per-region-counts.md` (to be created) |

## Numbered sections

### §1 The summary carries per-region counts
Extend the mapping at `tinyetl/load.py:26-32` with a `region_counts` key mapping each region seen
in the batch to the number of rows written for it. `row_count` is untouched and keeps meaning the
total.
**Reuse:** `tinyetl/load.py::summary`
**Acceptance criterion:** `python -m unittest tests.test_summary` passes, covering a mixed-region
batch where the per-region values sum to `row_count`.

### §2 The counts are computed where the rows are known
The writer at `tinyetl/load.py:13` `def write_records` is the only place that knows what was
written, so the per-region tally is derived there and handed to §1 rather than recomputed.
**Acceptance criterion:** `python -m unittest tests.test_summary` passes with a case asserting a
dry run reports zero for every region and does not write a file.

### §3 The emission site passes the tally through
`tinyetl/cli.py:32` `row_count` currently carries the only figure the printer receives; it also
passes the §2 tally, and the printed JSON stays sorted and single-line.
**Model-on:** `tinyetl/cli.py`
**Acceptance criterion:** `python -m unittest tests.test_cli` passes unchanged, and the printed
line parses as one JSON object carrying both keys.

### §4 Name what each reader must do
Add `docs/adr/0003-summary-adds-per-region-counts.md` recording the additive change and, per
reader, what it must do: `reporting-daily` may start charting the new key at its own pace, and
`alerting-hourly` keeps paging on `row_count` and must not switch to the per-region map.
**Acceptance criterion:** `python -m unittest tests.test_docs` passes, asserting the ADR file
exists, is numbered 0003, and names both `reporting-daily` and `alerting-hourly` with one action
each.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |

## Definition of Done (this spec)

- Every section's acceptance criterion holds under `python -m unittest discover -s tests -t .`.
- Generated / mirrored / snapshot artifacts downstream of touched surfaces: none — the summary is
  emitted, not stored, and no golden fixture of it is kept in this repo.
- §4's ADR is merged in the same wave as §1, so no reader sees the new shape undocumented.
