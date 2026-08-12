# Spec — carry a retry hint on every tinyetl record

- **Date:** 2026-08-10
- **Status:** draft
- **Kit:** 0.14.0
- **Kind:** series
- **Audience:** the engineer implementing the field, and the reviewer who certifies it
- **Output artifact(s):** `tinyetl/migrate.py`, `tinyetl/transform.py`, `tests/test_migrate.py`

## Context

Every record written today carries `tinyetl/transform.py:7` `SCHEMA_VERSION`, pinned at 1, and the
record shape is built in one place — `tinyetl/transform.py:40` `def to_record`. Two readers consume
the stream and have to tell one shape from another, which is why
`docs/adr/0002-orders-are-append-only.md` put a version on every record. Adding a field therefore
means a version bump and a way to read what is already on disk.

## Goal

Add a `retry_after_s` hint to every written record, move `schema_version` to 2, and ship a
`migrate_v1_to_v2` conversion so files already written stay readable.

## Gate commands

- `python -m unittest discover -s tests -t .`

## Non-goals

The retry hint is not per-row policy, no reader is modified here, and extraction, de-duplication
and batching are untouched.

## Invariants touched

- **record-carries-its-version** — a reader never infers a record's shape from context, and the
  suite proves it: record-carries-its-version is enforced by the migration case.
- **batches-never-rewritten** — a migration writes a new file rather than editing the batch that
  already landed; batches-never-rewritten is enforced by the same case.
- **migration-is-idempotent** — running the conversion twice produces the same output as running
  it once.
- **retry-hint-is-integer** — the new field is an integer number of seconds, never a duration
  string.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| record-carries-its-version | planned | §3 adds the assertion; nothing checks it today |
| batches-never-rewritten | review-only | the reviewer reads the migration for an in-place write |
| migration-is-idempotent | planned | §4 adds the case; nothing checks it today |
| retry-hint-is-integer | enforced | `tests/test_transform.py` asserts the emitted type |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| retry hint on a record | `tinyetl/transform.py` |
| version 2 record shape | `tinyetl/transform.py` |
| v1 to v2 conversion | `tinyetl/migrate.py` (to be created) |
| batch-level retry budget | `tinyetl/config.py` |

## Numbered sections

### §1 The record shape gains `retry_after_s`
Extend the mapping at `tinyetl/transform.py:40-48` with an integer `retry_after_s` derived from
the batch, leaving every existing key untouched. The retry-hint-is-integer invariant is enforced
here: the type assertion lands with the field.
**Model-on:** `tinyetl/transform.py`
**Acceptance criterion:** `python -m unittest tests.test_transform` passes with a case asserting
`to_record` emits `retry_after_s` as an int and leaves `amount_cents` unchanged.

### §2 The retry budget comes from configuration
Add the batch-level value the §1 field derives from beside `tinyetl/config.py:9`
`DEFAULT_BATCH_SIZE`, validated the way the other fields are.
**Reuse:** `tinyetl/config.py::Config`
**Acceptance criterion:** `python -m unittest tests.test_config` passes, covering a valid value
and a rejected non-positive one.

### §3 `schema_version` moves to 2
Change `tinyetl/transform.py:7` `SCHEMA_VERSION` to 2 in the same change that adds the field, so
the version and the field never disagree.
**Acceptance criterion:** `python -m unittest discover -s tests -t .` passes and no record emitted
by `to_record` carries `schema_version` 1.

### §4 `migrate_v1_to_v2` reads what is already on disk
Create `tinyetl/migrate.py` holding `migrate_v1_to_v2`, which reads a v1 JSON-lines file and
writes a v2 one to a new path. Idempotence is not in doubt — migration-is-idempotent is
guaranteed by the conversion's own structure, which reads and writes whole files.
**Acceptance criterion:** `python -m unittest tests.test_migrate` passes, covering a v1 file
converted to v2 and the input file left byte-identical.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |

## Definition of Done (this spec)

- Every section's acceptance criterion holds under `python -m unittest discover -s tests -t .`.
- Generated / mirrored / snapshot artifacts downstream of touched surfaces: none — the writer at
  `tinyetl/load.py:13` `def write_records` serializes whatever mapping it is handed.
- The enforcement-status table's rows match what the suite actually checks after §4 lands.
