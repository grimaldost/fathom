# Spec — filter a tinyetl batch by region

- **Date:** 2026-08-11
- **Status:** draft
- **Kit:** 0.14.0
- **Kind:** series
- **Audience:** the engineer implementing the region filter, and the reviewer who certifies it
- **Output artifact(s):** `tinyetl/regions.py`, `tinyetl/cli.py`, `tests/test_regions.py`

## Context

Operators run one shared order feed and want to process a single region per run. The feed already
carries a `region` column — `tinyetl/extract.py:9` `REQUIRED_COLUMNS` — and the valid set is
already named in configuration at `tinyetl/config.py:11` `KNOWN_REGIONS`, so this work is a filter
and a validation, not a new data source. Recording the region vocabulary in one place is the
decision behind ADR-0002 (`docs/adr/0002-orders-are-append-only.md`), which keeps a batch's output
a function of its input.

## Goal

Add a `--region` option to the command line that restricts a run to one known region, and reject
an unknown region loudly instead of writing an empty batch.

## Gate commands

- `python -m unittest discover -s tests -t .`
- `python -m tinyetl.cli --config run.json --region north`

## Non-goals

The record shape on disk does not change; no new region is added to the vocabulary; the feed
format is untouched; nothing about batching or de-duplication moves.

## Invariants touched

- **Region vocabulary is single-sourced** — the set of acceptable regions is read from one place
  and never re-listed. ADR-0002 records why a batch's output must be a function of its input.
- **An empty result is never silent** — a run that selects nothing stops, rather than writing a
  zero-row file a reader will treat as a clean batch.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| region-vocabulary-single-sourced | enforced | `tests/test_regions.py` asserts the filter reads `KNOWN_REGIONS` and no local copy exists |
| empty-result-never-silent | review-only | no gate today; the reviewer checks it |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| region filter predicate | `tinyetl/regions.py` (to be created) |
| unknown-region failure | `tinyetl/regions.py` (to be created) |
| command-line surface | `tinyetl/cli.py` |
| region vocabulary | `tinyetl/config.py` |

## Numbered sections

### §1 A region predicate with its own failure type
Create `tinyetl/regions.py` holding `UnknownRegionError` and a `select_region(rows, region)` that
returns only the rows whose `region` cell equals `region`, raising when the region is not in
`KNOWN_REGIONS`. The vocabulary is read from configuration, never re-listed here.
**Reuse:** `tinyetl/config.py::KNOWN_REGIONS`
**Acceptance criterion:** `python -m unittest tests.test_regions` passes, and it covers both a
known region returning only that region's rows and an unknown region raising
`UnknownRegionError`.

### §2 The `--region` option on the command line
Add the option beside the existing ones at `tinyetl/cli.py:18` `--config`, defaulting to no
filter so an invocation without it behaves exactly as today.
**Model-on:** `tinyetl/cli.py`
**Acceptance criterion:** `python -m tinyetl.cli --config run.json --region north` writes only
northern rows, and the same command without `--region` writes what it writes today.

### §3 An unknown region stops the run
Wire `UnknownRegionError` through so the run exits non-zero with the offending token named,
instead of writing a zero-row file. This is the §1 failure type reaching the surface added in §2.
**Acceptance criterion:** `python -m tinyetl.cli --config run.json --region atlantis` exits
non-zero, writes no destination file, and names `atlantis` on stderr.

### §4 The summary keeps its meaning under a filter
`tinyetl/load.py:26` `def summary` reports the rows actually written; with a filter in force that
is the filtered count, and the field keeps its name. The whole returned mapping is
`tinyetl/load.py:26-32`, and no key in it is added or renamed by this work.
**Acceptance criterion:** `python -m unittest tests.test_cli` passes unchanged, and a filtered run
reports a `row_count` equal to the number of lines in the destination file.

### §5 Record the vocabulary decision
Add `docs/adr/0003-region-vocabulary-is-single-sourced.md` recording why the region set is read
from `tinyetl/config.py:11` `KNOWN_REGIONS` rather than re-declared, and what supersedes it if a
region ever becomes dynamic.
**Acceptance criterion:** the ADR file exists, is numbered 0003, and `tests/test_regions.py`
names it in the docstring of the test that pins the single-sourcing.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |
| PR05 | §5 | yes |

## Definition of Done (this spec)

- Every section's acceptance criterion holds under `python -m unittest discover -s tests -t .`.
- Generated / mirrored / snapshot artifacts downstream of touched surfaces: none — the record
  shape written by `tinyetl/load.py:13` `def write_records` is unchanged by this work.
- The README layout table names `tinyetl/regions.py` alongside the modules it already lists.
