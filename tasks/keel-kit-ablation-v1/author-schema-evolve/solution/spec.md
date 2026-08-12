# Spec — carry a retry hint on every tinyetl record

- **Date:** 2026-08-11
- **Status:** draft
- **Kit:** 0.14.0
- **Kind:** series
- **Audience:** the engineer implementing the field, and the reviewer who certifies it
- **Output artifact(s):** `tinyetl/migrate.py`, `tinyetl/transform.py`, `tests/test_migrate.py`

## Context

Every record written today carries `tinyetl/transform.py:7` `SCHEMA_VERSION`, pinned at 1, and the
record shape is built in one place — `tinyetl/transform.py:40` `def to_record`. Two readers
consume the stream and have to tell one shape from another, which is the reason
`docs/adr/0002-orders-are-append-only.md` put a version on every record in the first place. Adding
a field therefore means a version bump and a way to read what is already on disk.

## Goal

Add a `retry_after_s` hint to every written record, move `schema_version` to 2, and ship a
`migrate_v1_to_v2` conversion so files already written stay readable.

## Gate commands

- `python -m unittest discover -s tests -t .`
- `python -m tinyetl.cli --config run.json`

## Non-goals

The retry hint is not per-row policy, no reader is modified here, and nothing about extraction,
de-duplication or batching changes.

## Invariants touched

- **A record's shape is identified by its own version field** — a reader must never infer the
  shape from context. Recorded in `docs/adr/0002-orders-are-append-only.md`.
- **Written batches are never rewritten in place** — migration produces a new file, never an edit
  of the batch that already landed. Same ADR.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| record-carries-its-version | enforced | `tests/test_migrate.py` asserts every record emitted by `to_record` carries `schema_version` |
| batches-never-rewritten | review-only | no gate today; the reviewer checks the migration writes a new path |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| retry hint on a record | `tinyetl/transform.py` |
| version 2 record shape | `tinyetl/transform.py` |
| v1 to v2 conversion | `tinyetl/migrate.py` (to be created) |
| batch-level retry budget | `tinyetl/config.py` |

## Numbered sections

### §1 The record shape gains `retry_after_s`
Extend the mapping returned at `tinyetl/transform.py:40-48` with an integer `retry_after_s`
derived from the batch, not from the row, and leave every existing key untouched.
**Model-on:** `tinyetl/transform.py`
**Acceptance criterion:** `python -m unittest tests.test_transform` passes with a new case
asserting `to_record` emits `retry_after_s` as an int and leaves `amount_cents` unchanged.

### §2 The retry budget comes from configuration
Add the batch-level value the §1 field is derived from beside
`tinyetl/config.py:9` `DEFAULT_BATCH_SIZE`, with the same validation shape the other fields use.
**Reuse:** `tinyetl/config.py::Config`
**Acceptance criterion:** `python -m unittest tests.test_config` passes, covering a valid value
and a rejected non-positive one.

### §3 `schema_version` moves to 2
Change `tinyetl/transform.py:7` `SCHEMA_VERSION` to 2 in the same change that adds the field, so
no record is ever written carrying version 1 with the new key.
**Acceptance criterion:** `python -m unittest discover -s tests -t .` passes, and no record
emitted by `to_record` carries `schema_version` 1.

### §4 `migrate_v1_to_v2` reads what is already on disk
Create `tinyetl/migrate.py` holding `migrate_v1_to_v2`, which reads a v1 JSON-lines file and
writes a v2 one to a new path, filling the §1 field with the configured default. It never edits
the input.
**Acceptance criterion:** `python -m unittest tests.test_migrate` passes, covering a v1 file
converted to v2 and the input file left byte-identical.

### §5 Record the shape-versioning decision
Add `docs/adr/0003-record-shape-versioning.md` recording why the field and the version bump ship
together, and what a reader must do when it sees a version it does not know.
**Acceptance criterion:** the ADR exists, is numbered 0003, and `tests/test_migrate.py` names it
in the docstring of the case that pins the version bump.

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
- Generated / mirrored / snapshot artifacts downstream of touched surfaces: none — the writer at
  `tinyetl/load.py:13` `def write_records` serializes whatever mapping it is handed.
- The README layout table names `tinyetl/migrate.py` alongside the modules it already lists.
