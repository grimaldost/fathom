# ADR-0002: The record stream is append-only

- **Status:** Accepted
- **Date:** 2026-02-17

## Context

Two downstream jobs read the JSON-lines file `tinyetl.load` writes. Rewriting a
record in place would give the two readers different histories depending on when
they ran.

## Decision

The destination file is written once per batch and never edited in place. A
correction is a new batch, not a rewrite. `schema_version` is carried on every
record so a reader can tell which shape it is holding.

## Consequences

Any change to the record shape needs a `schema_version` bump and a migration
note for both readers; the invariant is review-only today — nothing in the test
suite enforces it.
