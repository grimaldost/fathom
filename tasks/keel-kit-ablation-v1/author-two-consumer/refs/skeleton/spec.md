# Spec — per-region counts in the run summary

- **Date:** 2026-08-11
- **Status:** draft
- **Kind:** series
- **Audience:** the implementing engineer
- **Output artifact(s):** tinyetl/load.py, tinyetl/cli.py

## Context

Two jobs read the run summary: reporting-daily charts the volume and alerting-hourly pages when it
drops to zero. Adding a field to the summary is a change both of them see.

## Goal

Report per-region counts alongside the existing total without changing what the total means.

## Gate commands

The project's test suite.

## Non-goals

Neither reader is modified here and the record shape on disk is untouched.

## Invariants touched

An emitted field never changes meaning under its own name, and every consumer of the summary is
named before its shape moves.

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| per-region counts | `tinyetl/load.py` |
| summary emission | `tinyetl/cli.py` |

## Numbered sections

### §1 Per-region counts in the summary
The summary gains a mapping from region to the number of rows written for that region, and
row_count keeps its current name and meaning.
**Acceptance criterion:** the per-region values sum to the total the summary already reports.

### §2 Compute the counts where the rows are known
The tally is derived where the rows are written rather than recomputed later.
**Acceptance criterion:** a dry run reports zero for every region and writes nothing.

### §3 Pass the tally to the printer
The command line passes the tally through to the printed summary, which stays one JSON object.
**Acceptance criterion:** the printed line parses as a single JSON object carrying both keys.

### §4 Consumer notes
Record what each reader does: reporting-daily may adopt the new key at its own pace and
alerting-hourly keeps using the total.
**Acceptance criterion:** both readers are named with one action each.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |

## Definition of Done (this spec)

- The test suite passes and both readers keep working.
- Generated or mirrored artifacts downstream of this change: none.
