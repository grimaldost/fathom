# Spec — transforms become a package

- **Date:** 2026-08-11
- **Status:** draft
- **Kind:** series
- **Audience:** the implementing engineer
- **Output artifact(s):** tinyetl/transforms/

## Context

The transform module carries three unrelated responsibilities and every new rule lands in the
same file.

## Goal

Split it into a tinyetl/transforms/ package with one module per responsibility, keeping the public
names importable where they are imported today.

## Gate commands

The project's test suite.

## Non-goals

No behaviour changes and no caller outside the package changes an import.

## Invariants touched

Public import paths survive the move and the move is behaviour-preserving.

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| re-export surface | `tinyetl/transforms/__init__.py` (to be created) |
| currency normalization | `tinyetl/transforms/currency.py` (to be created) |
| de-duplication | `tinyetl/transforms/dedupe.py` (to be created) |
| record shaping | `tinyetl/transforms/records.py` (to be created) |

## Numbered sections

### §1 Create the package and move normalize_currency
Create tinyetl/transforms/__init__.py and tinyetl/transforms/currency.py and move the currency
rules there unchanged.
**Acceptance criterion:** the suite passes with no test edited and the new module imports.

### §2 Move dedupe_orders
Move de-duplication into tinyetl/transforms/dedupe.py with its failure type.
**Acceptance criterion:** the suite passes unchanged, including the missing-order-id case.

### §3 Move record shaping
Move the record builder into tinyetl/transforms/records.py, importing normalization from §1.
**Acceptance criterion:** the emitted record keys are identical to those emitted before the move.

### §4 Keep the old import path working
The old module becomes a shim re-exporting the three names so callers keep their imports.
**Acceptance criterion:** the suite passes with no test edited and the command line still runs.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |

## Definition of Done (this spec)

- The suite passes and no caller edits an import.
- Generated or mirrored artifacts downstream of this change: the README module table.
