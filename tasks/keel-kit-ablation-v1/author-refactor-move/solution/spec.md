# Spec — split the tinyetl transform module into a package

- **Date:** 2026-08-11
- **Status:** draft
- **Kit:** 0.14.0
- **Kind:** series
- **Audience:** the implementing engineer, and the reviewer who certifies the move
- **Output artifact(s):** `tinyetl/transforms/`, `tinyetl/transform.py`

## Context

`tinyetl/transform.py` now carries three unrelated responsibilities in one file: currency
normalization at `tinyetl/transform.py:14` `def normalize_currency`, de-duplication at
`tinyetl/transform.py:25` `def dedupe_orders`, and record shaping at
`tinyetl/transform.py:40` `def to_record`. Every new rule lands in the same file and the tests
import all three from one place — `tests/test_transform.py:3` `from tinyetl.transform import`.
This is a move, so the anchors above are pre-move positions and stop resolving once §1 lands;
they are recorded here as the state the move starts from.

## Goal

Turn the module into a `tinyetl/transforms/` package with one module per responsibility, keeping
every public name importable exactly where callers import it today.

## Gate commands

- `python -m unittest discover -s tests -t .`
- `python -m tinyetl.cli --config run.json`

## Non-goals

No behaviour changes, no signature changes, no test is rewritten, and no caller outside the
package changes an import.

## Invariants touched

- **Public import paths survive a move** — `normalize_currency`, `dedupe_orders` and `to_record`
  stay importable from `tinyetl.transform`, so no caller is edited in this wave.
- **A move is behaviour-preserving** — the suite passes unchanged, with no test edited to
  accommodate the new layout.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| public-import-paths-survive | enforced | `tests/test_transform.py` imports the three names unchanged and must pass without edits |
| move-is-behaviour-preserving | review-only | no gate proves a diff is behaviour-preserving; the reviewer reads it |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| package re-export surface | `tinyetl/transforms/__init__.py` (to be created) |
| currency normalization | `tinyetl/transforms/currency.py` (to be created) |
| order de-duplication | `tinyetl/transforms/dedupe.py` (to be created) |
| record shaping | `tinyetl/transforms/records.py` (to be created) |
| legacy import shim | `tinyetl/transform.py` |

## Numbered sections

### §1 Create the package and move currency normalization
Create `tinyetl/transforms/__init__.py` and `tinyetl/transforms/currency.py`, moving
`normalize_currency` and the currency vocabulary at `tinyetl/transform.py:5-7` into the latter,
unchanged.
**Acceptance criterion:** `python -m unittest tests.test_transform` passes with no edit to the
test file, and `python -c "import tinyetl.transforms.currency"` succeeds.

### §2 Move de-duplication
Move `dedupe_orders` into `tinyetl/transforms/dedupe.py` with its failure type, leaving the
behaviour and the message text alone.
**Acceptance criterion:** `python -m unittest tests.test_transform` passes unchanged, including
the case that asserts a row without an order id raises.

### §3 Move record shaping
Move `to_record` and the mapping it builds at `tinyetl/transform.py:40-48` into
`tinyetl/transforms/records.py`, which imports currency normalization from §1 rather than
re-implementing it.
**Reuse:** `tinyetl/transform.py::to_record`
**Acceptance criterion:** `python -m unittest tests.test_transform` passes unchanged, and the
record keys emitted are identical to those emitted before the move.

### §4 Keep the old import path working
Reduce `tinyetl/transform.py` to a shim that re-exports the three names from the package, so
`tinyetl/cli.py` and the tests keep their current imports.
**Model-on:** `tinyetl/cli.py`
**Acceptance criterion:** `python -m unittest discover -s tests -t .` passes with no test edited,
and `python -m tinyetl.cli --config run.json` behaves as it did before §1.

### §5 Record the layout decision
Add `docs/adr/0003-transforms-are-a-package.md` recording why the split happened, why the shim
stays, and when the shim may be removed.
**Acceptance criterion:** the ADR exists, is numbered 0003, and names the condition under which
`tinyetl/transform.py` is deleted.

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
- Generated / mirrored / snapshot artifacts downstream of touched surfaces: the README layout
  table names `tinyetl/transform.py` and is updated in the same wave as §4; there is no other
  mirror of the module list in this repo.
- No consumer outside the package edits an import; §4 is what makes that true.
