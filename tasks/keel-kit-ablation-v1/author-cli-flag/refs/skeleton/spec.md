# Spec — region filter for tinyetl

- **Date:** 2026-08-11
- **Status:** draft
- **Kind:** series
- **Audience:** the implementing engineer
- **Output artifact(s):** tinyetl/regions.py, tinyetl/cli.py

## Context

Operators want to run one region at a time. The feed already carries a region column and the
valid regions are already configured, so this is a filter rather than a new source.

## Goal

Add a `--region` option that limits a run to one known region and fails loudly on an unknown one.

## Gate commands

The project's test suite, and a manual run of the command line.

## Non-goals

The record shape does not change and no new region is introduced.

## Invariants touched

The set of acceptable regions stays single-sourced, and a run that selects nothing must not look
like a clean empty batch.

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| region filter | `tinyetl/regions.py` (to be created) |
| command-line surface | `tinyetl/cli.py` |
| region vocabulary | `tinyetl/config.py` |

## Numbered sections

### §1 Region filter module
Create tinyetl/regions.py with the filter and an `UnknownRegionError`, reading the region
vocabulary from configuration rather than re-listing it.
**Acceptance criterion:** the filter returns only rows for the requested region and raises for
an unknown one.

### §2 Command-line option
Add the `--region` option to the command line, defaulting to no filter.
**Acceptance criterion:** running with the option filters the batch and running without it
behaves as before.

### §3 Unknown region handling
An unknown region stops the run instead of writing an empty file.
**Acceptance criterion:** an unknown region is reported to the operator and no output file is
written.

### §4 Summary stays correct
The run summary reports the number of rows actually written under the filter, using the existing
KNOWN_REGIONS vocabulary for validation.
**Acceptance criterion:** the reported count matches the rows written for the selected region.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |

## Definition of Done (this spec)

- The test suite passes and the command line behaves as described.
- Generated or mirrored artifacts downstream of this change: none.
