# Spec — accept lower-case currency codes

- **Date:** 2026-08-11
- **Status:** draft
- **Kit:** 0.14.0
- **Kind:** single-change
- **Audience:** the implementing engineer, and the reviewer who certifies it
- **Output artifact(s):** `tinyetl/transform.py`, `tests/test_transform.py`

*This spec declares `Kind: single-change`: it is one function's behaviour, one PR, and there is
nothing to decompose. The declaration relaxes the three structural sections to absent-ok; it does
not relax the observable condition that means the change is done, which is recorded below.*

## Context

`tinyetl/transform.py:14` `def normalize_currency` accepts only the exact upper-case forms listed
at `tinyetl/transform.py:5` `SUPPORTED_CURRENCIES`, so a feed emitting `eur` has every row
rejected at `tinyetl/transform.py:40` `def to_record`. The vocabulary itself is correct; only the
comparison is case-sensitive.

## Goal

Make `normalize_currency` fold its `currency_code` argument to upper case before the membership
test, and keep rejecting anything that is not a supported currency in any case.

## Gate commands

- `python -m unittest discover -s tests -t .`

## Non-goals

No currency is added to or removed from the vocabulary, no other transform changes, and the
record shape on disk is untouched.

## Invariants touched

- **The currency vocabulary is single-sourced** — the accepted set stays the tuple at
  `tinyetl/transform.py:5-7`, and no caller keeps a second copy.
  `docs/adr/0002-orders-are-append-only.md` records why the written shape must be a function of
  the input alone.
- **An unsupported code always raises** — the failure stays a `ValueError` subclass, so callers
  that catch it keep working.

## Enforcement status

| Invariant | Status | Gate/mechanism |
|---|---|---|
| currency-vocabulary-single-sourced | enforced | `tests/test_transform.py` asserts the accepted set is exactly `SUPPORTED_CURRENCIES` |
| unsupported-code-always-raises | enforced | `tests/test_transform.py` covers an unsupported code in both letter cases |

## Concept → module map

| Concept introduced/changed | Module / file it lives in |
|---|---|
| case-insensitive currency comparison | `tinyetl/transform.py` |
| currency vocabulary | `tinyetl/transform.py` |

## The change

`normalize_currency` upper-cases `currency_code` before testing membership and returns the
canonical form. **Reuse:** `tinyetl/transform.py::SUPPORTED_CURRENCIES`

**Acceptance criterion:** `python -m unittest tests.test_transform` passes with two added cases —
`normalize_currency("eur")` returns `"EUR"`, and `normalize_currency("xyz")` raises the same
`ValueError` subclass with the same message shape as today.

## Definition of Done (this spec)

- `python -m unittest discover -s tests -t .` is green.
- Generated / mirrored / snapshot artifacts downstream of touched surfaces: none — the record
  written by `tinyetl/load.py:13` `def write_records` is unchanged.
- One PR, one concern; there is no manifest because there is nothing to decompose.
