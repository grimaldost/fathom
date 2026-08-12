# ADR-0001: Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-02-03

## Context

tinyetl is small, but the decisions that shape it (what the record contract is,
what may change without a consumer migration) outlive any one contributor.

## Decision

Every non-obvious design choice is recorded as a numbered ADR under `docs/adr/`,
one decision per file, using the next free number on the current base.

## Consequences

An Accepted ADR is never edited to say something else; it is superseded by a
later one that names it.
