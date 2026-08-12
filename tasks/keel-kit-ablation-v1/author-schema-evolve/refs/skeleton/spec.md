# Spec — retry hint on tinyetl records

- **Date:** 2026-08-11
- **Status:** draft
- **Kind:** series
- **Audience:** the implementing engineer
- **Output artifact(s):** tinyetl/migrate.py, tinyetl/transform.py

## Context

The two readers of the record stream guess how long to wait when a batch lands late. Records
already carry a version field, so a new field means a version bump and a migration.

## Goal

Add a retry hint to every record, move the schema version forward, and provide a conversion for
files already written.

## Gate commands

The project's test suite.

## Non-goals

No reader changes here, and extraction and batching are untouched.

## Invariants touched

A record's shape is identified by its own version field, and a batch already written is never
rewritten in place.

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| retry hint | `tinyetl/transform.py` |
| conversion | `tinyetl/migrate.py` (to be created) |
| retry budget | `tinyetl/config.py` |

## Numbered sections

### §1 Add the field
Every record gains a `retry_after_s` integer derived from the batch rather than the row.
**Acceptance criterion:** records written by the transform carry the new field as an integer.

### §2 Configuration for the budget
The value the field is derived from is configured alongside the other batch settings.
**Acceptance criterion:** a valid value is accepted and a non-positive one is rejected.

### §3 Bump the version
The `schema_version` on every record moves from 1 to 2 in the same change that adds the field.
**Acceptance criterion:** no record is written carrying the old version with the new field.

### §4 Migration for existing files
Create tinyetl/migrate.py providing `migrate_v1_to_v2`, which reads a v1 file and writes a v2 one
to a new path.
**Acceptance criterion:** an existing v1 file converts to v2 and the original is left unchanged.

## PR ↔ section manifest

| PR | Implements section | One concern? |
|---|---|---|
| PR01 | §1 | yes |
| PR02 | §2 | yes |
| PR03 | §3 | yes |
| PR04 | §4 | yes |

## Definition of Done (this spec)

- The test suite passes and existing files stay readable.
- Generated or mirrored artifacts downstream of this change: none.
